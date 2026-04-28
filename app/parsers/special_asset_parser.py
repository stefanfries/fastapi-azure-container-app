"""
Parser plugin for special (non-tradeable) asset classes: INDEX, COMMODITY, CURRENCY.

These instruments are not directly tradeable — they are only accessible via
derivative products such as warrants, certificates, or ETFs. Consequently they
have no trading venues and no id_notations on comdirect.

HTML differences vs. standard assets:
    - WKN is at position 2 in the H2 text (e.g. "WKN WKN846900") instead of position 1.
    - No ISIN is shown on the page.
    - No #marketSelect dropdown and no venue table.
"""

from bs4 import BeautifulSoup

from app.models.instrument_details import (
    CommodityDetails,
    CurrencyDetails,
    IndexDetails,
    InstrumentDetails,
)
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import (
    clean_numeric_value,
    extract_name_from_h1,
    extract_table_cell_by_label,
    extract_wkn_from_h2,
)


class SpecialAssetParser(InstrumentParser):
    """
    Parser for INDEX, COMMODITY, and CURRENCY asset classes.

    These asset classes share a slightly different comdirect HTML layout from
    standard assets and carry no trading-venue or id_notation information.
    """

    def __init__(self, asset_class: AssetClass) -> None:
        """
        Initialise the parser for a specific special asset class.

        Args:
            asset_class: One of AssetClass.INDEX, AssetClass.COMMODITY, or AssetClass.CURRENCY.
        """
        self._asset_class = asset_class

    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return self._asset_class

    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the H1 element.

        The comdirect H1 for special assets looks like e.g. "DAX Index" or
        "Gold Rohstoff". The asset-class label is kept as part of the name.
        """
        name = extract_name_from_h1(soup)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name

    def parse_wkn(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the WKN from the H2 element.

        For special assets the WKN sits at position 2 in the H2 token list
        (e.g. ['WKN', 'WKN846900'] → ['WKN', 'WKN', '846900']), unlike
        standard assets where it is at position 1.
        Returns None for instruments that have no WKN (e.g. some commodities).
        """
        return extract_wkn_from_h2(soup, position_offset=2)

    def parse_isin(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the ISIN from the Stammdaten table, if present.

        Most special assets (commodities, currencies) have no ISIN on comdirect.
        Some indices (e.g. MSCI indices) do carry an ISIN in the Stammdaten table.
        Returns None when the row is absent or contains "--".
        """
        isin = extract_table_cell_by_label(soup, "Stammdaten", "ISIN")
        if isin and isin.strip() not in ("--", "k. A.", ""):
            return isin.strip()
        return None

    def parse_id_notations(
        self,
        soup: BeautifulSoup,
        default_id_notation: str | None = None,
    ) -> tuple[
        dict[str, VenueInfo] | None,
        dict[str, VenueInfo] | None,
        str | None,
        str | None,
    ]:
        """
        Always returns (None, None, None, None).

        Special assets (indices, commodities, currencies) are not directly
        tradeable and therefore have no trading venues or id_notations.
        """
        return None, None, None, None

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        """
        Extract asset-class-specific Stammdaten for INDEX, COMMODITY, or CURRENCY.
        """
        if self._asset_class == AssetClass.INDEX:
            return self._parse_index_details(soup)
        if self._asset_class == AssetClass.COMMODITY:
            return self._parse_commodity_details(soup)
        if self._asset_class == AssetClass.CURRENCY:
            return self._parse_currency_details(soup)
        return None

    # ------------------------------------------------------------------
    # Private detail parsers
    # ------------------------------------------------------------------

    def _parse_index_details(self, soup: BeautifulSoup) -> IndexDetails:
        """
        Parse the "Stammdaten" table on a comdirect index page.

        German label → field mapping:
            Land             → country
            Landeswährung    → currency
            Enthaltene Werte → num_constituents (int)
            ISIN / WKN       → constituents_url  (e.g. "/v1/indices/DE0008469008")
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        identifier = _get("ISIN") or _get("WKN")
        constituents_url = f"/v1/indices/{identifier}" if identifier else None

        return IndexDetails(
            country=_get("Land"),
            currency=_get("Landeswährung"),
            num_constituents=clean_numeric_value(_get("Enthaltene Werte")),
            constituents_url=constituents_url,
        )

    def _parse_commodity_details(self, soup: BeautifulSoup) -> CommodityDetails:
        """
        Parse the "Stammdaten" table on a comdirect commodity page.

        German label → field mapping:
            Landeswährung   → currency
            Symbol          → symbol
            Land            → country
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        return CommodityDetails(
            currency=_get("Landeswährung"),
            symbol=_get("Symbol"),
            country=_get("Land"),
        )

    def _parse_currency_details(self, soup: BeautifulSoup) -> CurrencyDetails:
        """
        Parse the "Stammdaten" table on a comdirect currency page.

        German label → field mapping:
            Wechselkurs  → base_currency + quote_currency  (split "EUR/USD" on "/")
            Land         → country
        """
        section = "Stammdaten"

        def _get(label: str) -> str | None:
            v = extract_table_cell_by_label(soup, section, label)
            return v if v and v.strip() not in ("--", "k. A.") else None

        base_currency: str | None = None
        quote_currency: str | None = None
        exchange_rate = _get("Wechselkurs")
        if exchange_rate and "/" in exchange_rate:
            parts = exchange_rate.split("/", 1)
            base_currency = parts[0].strip() or None
            quote_currency = parts[1].strip() or None

        return CurrencyDetails(
            base_currency=base_currency,
            quote_currency=quote_currency,
            country=_get("Land"),
        )

