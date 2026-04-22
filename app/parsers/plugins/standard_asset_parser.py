"""
Parser plugin for STOCK asset class.

This parser handles the standard HTML structure used by stocks, bonds, ETFs,
funds, and certificates on comdirect.
"""

from bs4 import BeautifulSoup

from app.models.instrument_details import InstrumentDetails, StockDetails
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    clean_float_value,
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

    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """
        Extract the WKN from the HTML.

        For standard assets, WKN is in the H2 tag, extracted from patterns like:
        "WKN: 123456 / ISIN: DE0001234567"
        """
        wkn = extract_wkn_from_h2(soup)
        if not wkn:
            raise ValueError("Could not extract WKN from H2")
        return wkn

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
        """
        Extract asset-class-specific Stammdaten from the HTML.

        Currently implemented for STOCK only.  All other standard asset classes
        (BOND, ETF, FONDS, CERTIFICATE) return ``None`` until their parsers are
        extended.
        """
        if self._asset_class == AssetClass.STOCK:
            return self._parse_stock_details(soup)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_stock_details(self, soup: BeautifulSoup) -> StockDetails:
        """
        Parse the "Aktieninformationen" table on the comdirect stock page.

        The table uses these German header labels:
            Wertpapiertyp, Marktsegment, Branche, Geschäftsjahr,
            Marktkapital., Streubesitz, Nennwert, Stücke

        All fields are treated as optional — any missing or "--" value becomes None.
        """
        from app.parsers.plugins.parsing_utils import clean_numeric_value

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

        # Fiscal year end "DD.MM." → "MM-DD"
        import re

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
        nominal_value: float | None = None
        nominal_value_currency: str | None = None
        if nennwert_raw and nennwert_raw.strip() not in ("--", ""):
            parts = nennwert_raw.split()
            if parts and len(parts[-1]) == 3 and parts[-1].isupper():
                nominal_value_currency = parts[-1]
                nennwert_raw = " ".join(parts[:-1])
            nominal_value = clean_float_value(nennwert_raw)

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
