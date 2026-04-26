"""
Parser plugin for WARRANT asset class.

Inherits shared name/WKN/ISIN/id_notations logic from StandardAssetParser.
Warrants use a different Stammdaten HTML structure requiring custom detail extraction.
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.models.instrument_details import InstrumentDetails, WarrantDetails
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    clean_float_value,
    extract_preferred_ex_notation,
    extract_preferred_lt_notation,
    extract_venues_from_dropdown,
)
from app.parsers.standard_asset_parser import StandardAssetParser


class WarrantParser(StandardAssetParser):
    """Parser for WARRANT asset class (Optionsscheine)."""

    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return AssetClass.WARRANT

    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: str | None = None
    ) -> tuple[dict[str, VenueInfo] | None, dict[str, VenueInfo] | None, str | None, str | None]:
        """
        Extract trading venues and their ID_NOTATIONs from the HTML,
        including preferred notations based on liquidity.

        For warrants, trading venues are in the #marketSelect dropdown.
        comdirect always redirects any instrument lookup to a URL with ID_NOTATION
        already appended (platform-wide behaviour), so the dropdown is always present.

        Returns:
            Tuple of (lt_venue_dict, ex_venue_dict,
                      preferred_lt_id_notation, preferred_ex_id_notation)
        """
        # Extract venues from dropdown
        id_notations_dict = extract_venues_from_dropdown(soup)

        if not id_notations_dict:
            # If we still don't have notations, return empty dicts
            # This can happen if the page wasn't fetched with ID_NOTATION
            return None, None, None, None

        # Separate into Life Trading and Exchange Trading
        lt_venue_dict, ex_venue_dict = categorize_lt_ex_venues(id_notations_dict)

        # Extract preferred ID_NOTATIONs based on liquidity
        # Use single-venue fallback for warrants
        preferred_lt_id_notation = extract_preferred_lt_notation(
            soup, lt_venue_dict, use_single_venue_fallback=True
        )
        preferred_ex_id_notation = extract_preferred_ex_notation(
            soup, ex_venue_dict, use_single_venue_fallback=True
        )

        return lt_venue_dict, ex_venue_dict, preferred_lt_id_notation, preferred_ex_id_notation

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        """Extract warrant-specific Stammdaten from the HTML."""
        return self._parse_warrant_details(soup)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_warrant_details(self, soup: BeautifulSoup) -> WarrantDetails:
        """
        Parse the "Stammdaten" table on the comdirect warrant detail page.

        Extraction strategy for fields with rich HTML:
        - Typ:      Reconstructs text, replacing the abbreviated <span> display text
                    with its title attribute: "Call (Amer.)" → "Call (Amerikanisch)"
        - Basiswert: underlying_name from <span title>, underlying_link from <a href>
        - Emittent:  Full institution name from <a title>
        """

        def _section_table(heading: str):
            h2 = soup.find("h2", string=re.compile(heading))
            if not h2:
                return None
            return h2.parent.find("table")

        def _find_td(table, label: str):
            """Return the <td> Tag for the given <th> label, or None."""
            if table is None:
                return None
            for th in table.find_all("th"):
                if label in th.get_text(" ", strip=True):
                    td = th.find_next_sibling("td")
                    if td is None:
                        td = th.parent.find("td")
                    return td
            return None

        def _td_text(table, label: str) -> str | None:
            td = _find_td(table, label)
            if td is None:
                return None
            text = td.get_text(" ", strip=True).replace("\xa0", " ")
            return text if text and text not in ("--", "k. A.") else None

        def _td_text_span_title(table, label: str) -> str | None:
            """Reconstruct td text, swapping each <span title=…> display text for its title."""
            td = _find_td(table, label)
            if td is None:
                return None
            parts = []
            for child in td.children:
                if getattr(child, "name", None) == "span" and child.get("title"):
                    parts.append(child["title"])
                elif getattr(child, "name", None) is not None:
                    parts.append(child.get_text())
                else:
                    parts.append(str(child))
            result = "".join(parts).strip()
            return result if result and result not in ("--", "k. A.") else None

        def _parse_date(text: str | None) -> date | None:
            if not text:
                return None
            for fmt in ("%d.%m.%y", "%d.%m.%Y"):
                try:
                    return datetime.strptime(text.strip(), fmt).date()
                except ValueError:
                    continue
            return None

        table = _section_table("Stammdaten")

        # Typ: "Call (Amer.)" → "Call (Amerikanisch)" via span title
        warrant_type = _td_text_span_title(table, "Typ")

        # Basiswert: full name from <span title>, link from <a href>
        underlying_name: str | None = None
        underlying_link: str | None = None
        basiswert_td = _find_td(table, "Basiswert")
        if basiswert_td:
            a_tag = basiswert_td.find("a")
            if a_tag:
                span = a_tag.find("span")
                if span and span.get("title"):
                    underlying_name = span["title"].strip() or None
                elif a_tag.get("title"):
                    underlying_name = a_tag["title"].strip() or None
                else:
                    underlying_name = a_tag.get_text(strip=True) or None
                if underlying_name in ("--", "k. A.", ""):
                    underlying_name = None
                href = a_tag.get("href", "")
                if href:
                    underlying_link = (
                        f"https://www.comdirect.de{href}"
                        if href.startswith("/")
                        else href
                    )
            else:
                text = basiswert_td.get_text(" ", strip=True)
                underlying_name = text if text and text not in ("--", "k. A.") else None

        # Basispreis: "350,00 USD" → split value + currency
        strike_raw = _td_text(table, "Basispreis")
        strike: float | None = None
        strike_currency: str | None = None
        if strike_raw:
            parts = strike_raw.split()
            if len(parts) >= 2 and len(parts[-1]) == 3 and parts[-1].isupper():
                strike_currency = parts[-1]
                strike_raw = " ".join(parts[:-1])
            strike = clean_float_value(strike_raw)

        # Emittent: prefer the <a title="Issuer Name, Emittent Kontakt"> attribute,
        # taking only the part before the first comma to get the clean issuer name.
        # Falls back to display text if no title attribute is present.
        issuer: str | None = None
        emittent_td = _find_td(table, "Emittent")
        if emittent_td:
            a_tag = emittent_td.find("a", attrs={"title": True})
            if a_tag and a_tag["title"].strip() and a_tag["title"].strip() not in ("--", "k. A."):
                issuer = a_tag["title"].split(",")[0].strip()
            else:
                text = emittent_td.get_text(" ", strip=True).replace("\xa0", " ")
                issuer = text if text and text not in ("--", "k. A.") else None

        return WarrantDetails(
            warrant_type=warrant_type,
            underlying_name=underlying_name,
            underlying_link=underlying_link,
            strike=strike,
            strike_currency=strike_currency,
            ratio=_td_text(table, "Bezugsverhältnis"),
            maturity_date=_parse_date(_td_text(table, "Fälligkeit")),
            last_trading_day=_parse_date(_td_text(table, "letzter Handelstag")),
            issuer=issuer,
        )
