"""Parser for CERTIFICATE asset class."""

import re

from bs4 import BeautifulSoup

from app.models.instrument_details import CertificateDetails, InstrumentDetails
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import (
    clean_float_value,
    extract_table_cell_by_label,
)
from app.parsers.standard_asset_parser import StandardAssetParser


class CertificateParser(StandardAssetParser):
    """Parser for CERTIFICATE asset class (Zertifikate)."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.CERTIFICATE

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails:
        return self._parse_certificate_details(soup)

    def _parse_certificate_details(self, soup: BeautifulSoup) -> CertificateDetails:
        """
        Parse the "Stammdaten" table on the comdirect certificate page.

        German label → field mapping:
            Typ                 → certificate_type
            Basiswert           → underlying_name  (page-wide fallback used)
            Cap-Niveau          → cap + cap_currency  (e.g. "100,00 EUR")
            Absicherungsniveau/Barriere → barrier + barrier_currency
            Absich. erreicht?   → barrier_breached  (Bonus certs)
            Bonusniveau         → bonus_level + bonus_level_currency  (Bonus certs)
            Partizipationsrate  → participation_rate  (e.g. "100,00 %")
            Fälligkeit/Laufzeitende → maturity_date
            Emittent            → issuer
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
