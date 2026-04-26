"""
Parser plugin for STOCK asset class.

This parser handles the standard HTML structure used by stocks, bonds, ETFs,
funds, and certificates on comdirect.
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.models.instrument_details import (
    BondDetails,
    CertificateDetails,
    ETFDetails,
    FondsDetails,
    InstrumentDetails,
    StockDetails,
)
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    clean_float_value,
    clean_numeric_value,
    extract_after_label,
    extract_name_from_h1,
    extract_preferred_ex_notation,
    extract_preferred_lt_notation,
    extract_table_cell_by_label,
    extract_venue_from_single_table,
    extract_venues_from_dropdown,
    extract_wkn_from_h2,
)


class StandardAssetParser(InstrumentParser):
    """Parser for STOCK, BOND, ETF, FUND, and CERTIFICATE asset classes."""

    def __init__(self, asset_class: AssetClass):
        """
        Initialize the parser for a specific asset class.

        Args:
            asset_class: The asset class this parser will handle
        """
        self._asset_class = asset_class

    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return self._asset_class

    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the HTML.

        For standard assets, the name is in the H1 tag with the asset class
        name removed.
        """
        name = extract_name_from_h1(soup, remove_suffix=self.asset_class.comdirect_label)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name

    def parse_wkn(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the WKN from the HTML.

        For standard assets, WKN is in the H2 tag, extracted from patterns like:
        "WKN: 123456 / ISIN: DE0001234567"
        Returns None for foreign instruments where WKN is '--'.
        """
        return extract_wkn_from_h2(soup)

    def parse_isin(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the ISIN from the HTML.

        For standard assets, ISIN is in the H2 tag after "ISIN:"
        """
        return extract_after_label(soup, "ISIN:", max_length=12)

    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: str | None = None
    ) -> tuple[dict[str, VenueInfo] | None, dict[str, VenueInfo] | None, str | None, str | None]:
        """
        Extract trading venues and their ID_NOTATIONs from the HTML,
        including preferred notations based on liquidity.

        For standard assets, trading venues are in #marketSelect dropdown
        or in a table if there's only one venue.

        Returns:
            Tuple of (lt_venue_dict, ex_venue_dict,
                      preferred_lt_id_notation, preferred_ex_id_notation)
        """
        # Try dropdown first (multiple venues)
        id_notations_dict = extract_venues_from_dropdown(soup)

        # If no dropdown, try single-venue table
        if not id_notations_dict:
            id_notations_dict = extract_venue_from_single_table(soup)

        # Separate into Life Trading and Exchange Trading
        lt_venue_dict, ex_venue_dict = categorize_lt_ex_venues(id_notations_dict)

        # Extract preferred ID_NOTATIONs based on liquidity
        preferred_lt_id_notation = extract_preferred_lt_notation(soup, lt_venue_dict)
        preferred_ex_id_notation = extract_preferred_ex_notation(soup, ex_venue_dict)

        return lt_venue_dict, ex_venue_dict, preferred_lt_id_notation, preferred_ex_id_notation

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        """Extract asset-class-specific Stammdaten from the HTML."""
        if self._asset_class == AssetClass.STOCK:
            return self._parse_stock_details(soup)
        if self._asset_class == AssetClass.BOND:
            return self._parse_bond_details(soup)
        if self._asset_class == AssetClass.ETF:
            return self._parse_etf_details(soup)
        if self._asset_class == AssetClass.FONDS:
            return self._parse_fonds_details(soup)
        if self._asset_class == AssetClass.CERTIFICATE:
            return self._parse_certificate_details(soup)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(text: str | None) -> date | None:
        """Parse a German date string (DD.MM.YYYY or DD.MM.YY) into a date object."""
        if not text or text.strip() in ("--", "k. A.", ""):
            return None
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _split_value_currency(raw: str | None) -> tuple[float | None, str | None]:
        """Split a string like '100,00 EUR' into (100.0, 'EUR')."""
        if not raw or raw.strip() in ("--", ""):
            return None, None
        parts = raw.split()
        currency: str | None = None
        if parts and len(parts[-1]) == 3 and parts[-1].isupper():
            currency = parts[-1]
            raw = " ".join(parts[:-1])
        value = clean_float_value(raw)
        return value, currency

    def _parse_stock_details(self, soup: BeautifulSoup) -> StockDetails:
        """
        Parse the "Aktieninformationen" table on the comdirect stock page.

        The table uses these German header labels:
            Wertpapiertyp, Marktsegment, Branche, Geschäftsjahr,
            Marktkapital., Streubesitz, Nennwert, Stücke

        All fields are treated as optional — any missing or "--" value becomes None.
        """
        section = "Aktieninformationen"

        security_type = extract_table_cell_by_label(soup, section, "Wertpapiertyp")
        market_segment = extract_table_cell_by_label(soup, section, "Marktsegment")

        # "Branche" value is in a <span title="full name">truncated..</span>
        # We prefer the title attribute to avoid getting the truncated display text.
        sector: str | None = None
        section_node = soup.find(string=lambda t: t and section in t)
        if section_node:
            branche_th = section_node.parent.parent.find(
                "th", string=lambda t: t and "Branche" in t
            )
            if branche_th:
                td = branche_th.find_next_sibling("td")
                if td:
                    span = td.find("span")
                    if span and span.get("title"):
                        sector = span["title"].strip()
                    else:
                        raw = td.get_text(strip=True)
                        sector = raw if raw and raw != "--" else None

        # Fiscal year end "DD.MM." → "DD-MM"
        fye_raw = extract_table_cell_by_label(soup, section, "Geschäftsjahr")
        fiscal_year_end: str | None = None
        if fye_raw and fye_raw.strip() not in ("--", ""):
            m = re.match(r"(\d{1,2})\.(\d{1,2})\.", fye_raw.strip())
            if m:
                fiscal_year_end = f"{int(m.group(1)):02d}-{int(m.group(2)):02d}"

        # Market cap "4,20 Bil. EUR" — strip trailing currency code first
        market_cap_raw = extract_table_cell_by_label(soup, section, "Marktkapital.")
        market_cap: float | None = None
        market_cap_currency: str | None = None
        if market_cap_raw and market_cap_raw.strip() not in ("--", ""):
            parts = market_cap_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                market_cap_currency = parts[-1]
                market_cap_raw = " ".join(parts[:-1])
            numeric = clean_numeric_value(market_cap_raw)
            market_cap = float(numeric) if numeric is not None else None

        # Free float "68,46 %"
        free_float_raw = extract_table_cell_by_label(soup, section, "Streubesitz")
        free_float = clean_float_value(free_float_raw) if free_float_raw else None

        # Nominal value "0,00 USD" — split value from currency
        nennwert_raw = extract_table_cell_by_label(soup, section, "Nennwert")
        nominal_value, nominal_value_currency = self._split_value_currency(nennwert_raw)

        # Shares outstanding "24,30 Mrd."
        stuecke_raw = extract_table_cell_by_label(soup, section, "Stücke")
        shares_outstanding: float | None = None
        if stuecke_raw and stuecke_raw.strip() not in ("--", ""):
            numeric = clean_numeric_value(stuecke_raw)
            shares_outstanding = float(numeric) if numeric is not None else None

        return StockDetails(
            security_type=security_type if security_type and security_type != "--" else None,
            market_segment=market_segment if market_segment and market_segment != "--" else None,
            sector=sector,
            fiscal_year_end=fiscal_year_end,
            market_cap=market_cap,
            market_cap_currency=market_cap_currency,
            free_float=free_float,
            nominal_value=nominal_value,
            nominal_value_currency=nominal_value_currency,
            shares_outstanding=shares_outstanding,
        )

    def _parse_bond_details(self, soup: BeautifulSoup) -> BondDetails:
        """
        Parse the "Stammdaten" table on the comdirect bond page.

        German label → field mapping:
            Emittent          → issuer  (full name from <span title>)
            Nominalzinssatz   → coupon_rate_percent  (e.g. "10,250 %")
            Kupon-Art         → coupon_type  (e.g. "Fest")
            Ausgabedatum      → issue_date   (DD.MM.YYYY)
            Fälligkeit        → maturity_date
            Stückelung        → nominal_value + currency
            Typ               → bond_type
            Währung           → currency

        Note: Moody's and S&P ratings are not provided by comdirect.
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        issuer = _get("Emittent")
        coupon_rate_percent = clean_float_value(_get("Nominalzinssatz"))
        coupon_type = _get("Kupon-Art")
        issue_date = self._parse_date(_get("Ausgabedatum"))
        maturity_date = self._parse_date(_get("Fälligkeit"))
        nominal_value, currency_nw = self._split_value_currency(_get("Stückelung"))
        bond_type = _get("Typ")
        currency = _get("Währung") or currency_nw

        return BondDetails(
            issuer=issuer,
            coupon_rate_percent=coupon_rate_percent,
            coupon_type=coupon_type,
            issue_date=issue_date,
            maturity_date=maturity_date,
            nominal_value=nominal_value,
            bond_type=bond_type,
            currency=currency,
        )

    def _parse_etf_details(self, soup: BeautifulSoup) -> ETFDetails:
        """
        Parse the "Stammdaten" table on the comdirect ETF page.

        German label → field mapping:
            Vergleichsindex      → tracked_index  (full name from <span title>)
            Laufende Kosten      → expense_ratio_percent  (e.g. "0,20 %")
            Abbildungsart        → replication_method
            Art                  → distribution_policy
            Auflagedatum         → inception_date  (not always present)
            Währung              → fund_currency
            Fondsvolumen         → fund_size  (e.g. "1,23 Mrd. EUR")

        Note: Fondsdomizil is not provided by comdirect.
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        tracked_index = _get("Vergleichsindex")
        expense_ratio_percent = clean_float_value(_get("Laufende Kosten"))
        replication_method = _get("Abbildungsart")
        distribution_policy_raw = _get("Art")
        distribution_policy = " ".join(distribution_policy_raw.split()) if distribution_policy_raw else None
        inception_date = self._parse_date(_get("Auflagedatum"))
        fund_currency = _get("Währung")

        fund_size_raw = _get("Fondsvolumen")
        fund_size: float | None = None
        if fund_size_raw:
            # Strip trailing currency code before parsing magnitude (e.g. "311,39 Mio. EUR")
            parts = fund_size_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                parts = parts[:-1]
            numeric = clean_numeric_value(" ".join(parts))
            fund_size = float(numeric) if numeric is not None else None

        return ETFDetails(
            tracked_index=tracked_index,
            expense_ratio_percent=expense_ratio_percent,
            replication_method=replication_method,
            distribution_policy=distribution_policy,
            inception_date=inception_date,
            fund_currency=fund_currency,
            fund_size=fund_size,
        )

    def _parse_fonds_details(self, soup: BeautifulSoup) -> FondsDetails:
        """
        Parse the "Stammdaten" table on the comdirect mutual-fund page.

        German label → field mapping:
            Fondskategorie    → fund_type
            Fondsmanager      → fund_manager  (not always present)
            Auflagedatum      → inception_date  (not always present)
            Art               → distribution_policy
            Laufende Kosten   → expense_ratio_percent  (e.g. "1,50 %")
            Währung           → fund_currency
            Fondsvolumen      → fund_size  (e.g. "512,00 Mio.")

        Note: Fondsdomizil is not provided by comdirect.
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        fund_type = _get("Fondskategorie")
        fund_manager = _get("Fondsmanager")
        inception_date = self._parse_date(_get("Auflagedatum"))
        distribution_policy_raw = _get("Art")
        distribution_policy = " ".join(distribution_policy_raw.split()) if distribution_policy_raw else None
        expense_ratio_percent = clean_float_value(_get("Laufende Kosten"))
        fund_currency = _get("Währung")

        fund_size_raw = _get("Fondsvolumen")
        fund_size: float | None = None
        if fund_size_raw:
            # Strip trailing currency code before parsing magnitude (e.g. "512,00 Mio. EUR")
            parts = fund_size_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                parts = parts[:-1]
            numeric = clean_numeric_value(" ".join(parts))
            fund_size = float(numeric) if numeric is not None else None

        return FondsDetails(
            fund_type=fund_type,
            fund_manager=fund_manager,
            inception_date=inception_date,
            distribution_policy=distribution_policy,
            expense_ratio_percent=expense_ratio_percent,
            fund_currency=fund_currency,
            fund_size=fund_size,
        )

    def _parse_certificate_details(self, soup: BeautifulSoup) -> CertificateDetails:
        """
        Parse the "Stammdaten" table on the comdirect certificate page.

        German label → field mapping:
            Typ                 → certificate_type  (comdirect uses "Typ", older pages "Zertifikattyp")
            Basiswert           → underlying_name  (may be outside Stammdaten; page-wide fallback used)
            Cap-Niveau          → cap + cap_currency  (e.g. "100,00 EUR")
            Absicherungsniveau/Barriere → barrier + barrier_currency
            Absich. erreicht?   → barrier_breached  (Bonus certs)
            Bonusniveau         → bonus_level + bonus_level_currency  (Bonus certs)
            Partizipationsrate  → participation_rate  (e.g. "100,00 %")
            Fälligkeit /
            Laufzeitende        → maturity_date  (DD.MM.YYYY, "Open End", or "endlos" → None)
            Emittent            → issuer  (full name from <span title>)
            Währung             → currency
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        def _get_page(label: str) -> str | None:
            """Search for a label anywhere on the page (used for fields not in Stammdaten)."""
            for th in soup.find_all("th"):
                if re.search(label, th.get_text(" ", strip=True)):
                    td = th.find_next_sibling("td")
                    if td:
                        # Prefer <span title="Full Name"> over truncated display text.
                        span = td.find("span", attrs={"title": True})
                        v = span["title"].strip() if span and span["title"].strip() else td.get_text(" ", strip=True)
                        return v if v and v.strip() not in ("--", "k. A.") else None
            return None

        # "Typ" matches both "Typ" (current) and "Zertifikattyp" (older pages) via regex.
        certificate_type = _get("Typ")
        # "Basiswert" is not always in the Stammdaten section; fall back to page-wide search.
        underlying_name = _get("Basiswert") or _get_page("Basiswert")
        # "Cap" matches both "Cap" (Discount certs) and "Cap-Niveau" (older pages) via substring.
        cap, cap_currency = self._split_value_currency(_get("Cap"))
        # Bonus certs use "Absicherungsniveau"; older/other certs may use "Barriere".
        barrier, barrier_currency = self._split_value_currency(
            _get("Absicherungsniveau") or _get("Barriere")
        )
        barrier_breached_raw = _get("Absich. erreicht?")
        barrier_breached: bool | None = None
        if barrier_breached_raw:
            if barrier_breached_raw.lower() in ("ja", "yes"):
                barrier_breached = True
            elif barrier_breached_raw.lower() in ("nein", "no"):
                barrier_breached = False
        bonus_level, bonus_level_currency = self._split_value_currency(_get("Bonusniveau"))
        knockout, knockout_currency = self._split_value_currency(_get("Knock Out"))
        strike, strike_currency = self._split_value_currency(_get("Basispreis"))
        participation_rate = clean_float_value(_get("Partizipationsrate"))
        # comdirect uses "Laufzeitende" on current pages, older pages use "Fälligkeit".
        maturity_date = self._parse_date(_get("Laufzeitende|Fälligkeit"))
        issuer = _get("Emittent")
        # Use anchored regex to avoid matching "Währungsgesichert" when "Währung" label is absent.
        currency = _get("^Währung$")
        subscription_ratio = _get("Bez.-Verh.")
        region = _get("Region")
        currency_hedged_raw = _get("Währungs\xadgesichert") or _get("Währungsgesichert")
        currency_hedged: bool | None = None
        if currency_hedged_raw:
            if currency_hedged_raw.lower() in ("ja", "yes"):
                currency_hedged = True
            elif currency_hedged_raw.lower() in ("nein", "no"):
                currency_hedged = False

        return CertificateDetails(
            certificate_type=certificate_type,
            underlying_name=underlying_name,
            cap=cap,
            cap_currency=cap_currency,
            barrier=barrier,
            barrier_currency=barrier_currency,
            barrier_breached=barrier_breached,
            bonus_level=bonus_level,
            bonus_level_currency=bonus_level_currency,
            knockout=knockout,
            knockout_currency=knockout_currency,
            strike=strike,
            strike_currency=strike_currency,
            participation_rate=participation_rate,
            maturity_date=maturity_date,
            issuer=issuer,
            currency=currency,
            subscription_ratio=subscription_ratio,
            region=region,
            currency_hedged=currency_hedged,
        )
