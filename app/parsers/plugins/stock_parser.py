"""Parser for STOCK asset class."""

import re

from bs4 import BeautifulSoup

from app.models.instrument_details import InstrumentDetails, StockDetails
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import (
    clean_float_value,
    clean_numeric_value,
    extract_table_cell_by_label,
)
from app.parsers.plugins.standard_asset_parser import StandardAssetParser


class StockParser(StandardAssetParser):
    """Parser for STOCK asset class (Aktien)."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.STOCK

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails:
        return self._parse_stock_details(soup)

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
