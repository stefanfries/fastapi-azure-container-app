"""
Unit tests for app.parsers.special_asset_parser.SpecialAssetParser.

Covers asset_class property, parse_isin (from Stammdaten table),
parse_id_notations (always all-None tuple), and parse_details for
INDEX, COMMODITY, and CURRENCY asset classes.
"""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import CommodityDetails, CurrencyDetails, IndexDetails
from app.models.instruments import AssetClass
from app.parsers.special_asset_parser import SpecialAssetParser


class TestAssetClass:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_asset_class_roundtrip(self, asset_class):
        assert SpecialAssetParser(asset_class).asset_class == asset_class


class TestParseIsin:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_returns_none_when_no_stammdaten_isin(self, asset_class):
        """Returns None when the Stammdaten table has no ISIN row."""
        soup = _stammdaten_page([("Land", "Deutschland")])
        assert SpecialAssetParser(asset_class).parse_isin(soup) is None

    @pytest.mark.parametrize("placeholder", ["--", "k. A."])
    def test_returns_none_for_placeholder_isin(self, placeholder):
        """Returns None when the ISIN cell contains a placeholder value."""
        soup = _stammdaten_page([("ISIN", placeholder)])
        assert SpecialAssetParser(AssetClass.INDEX).parse_isin(soup) is None

    def test_extracts_isin_from_stammdaten(self):
        """Extracts a real ISIN when present in the Stammdaten table."""
        soup = _stammdaten_page([("ISIN", "DE0008469008")])
        assert SpecialAssetParser(AssetClass.INDEX).parse_isin(soup) == "DE0008469008"


class TestParseIdNotations:
    def test_returns_four_nones(self):
        """Special assets are not tradeable — no venues or id_notations."""
        parser = SpecialAssetParser(AssetClass.INDEX)
        lt, ex, lt_pref, ex_pref = parser.parse_id_notations(None)  # type: ignore[arg-type]
        assert lt is None
        assert ex is None
        assert lt_pref is None
        assert ex_pref is None


# ---------------------------------------------------------------------------
# parse_name — raises ValueError when no H1 found
# ---------------------------------------------------------------------------

class TestParseName:
    def test_raises_when_no_h1(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>nothing</p></body></html>", "html.parser")
        with pytest.raises(ValueError, match="H1 headline"):
            SpecialAssetParser(AssetClass.INDEX).parse_name(soup)

    def test_returns_full_name_without_suffix_removal(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><h1>DAX Index</h1></body></html>", "html.parser")
        assert SpecialAssetParser(AssetClass.INDEX).parse_name(soup) == "DAX Index"


# ---------------------------------------------------------------------------
# parse_wkn — raises ValueError when H2 yields nothing
# ---------------------------------------------------------------------------

class TestParseWkn:
    def test_returns_none_when_no_h2(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>no h2</p></body></html>", "html.parser")
        assert SpecialAssetParser(AssetClass.INDEX).parse_wkn(soup) is None

    def test_extracts_wkn_at_position_2(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(
            "<html><body><h2>WKN WKN WKN846900</h2></body></html>", "html.parser"
        )
        assert SpecialAssetParser(AssetClass.INDEX).parse_wkn(soup) == "WKN846900"

    def test_returns_none_for_double_dash_wkn(self):
        from bs4 import BeautifulSoup
        # Instruments without a WKN (e.g. L&S Brent Oil) have "--" at position 2
        soup = BeautifulSoup(
            "<html><body><h2>WKN WKN --</h2></body></html>", "html.parser"
        )
        assert SpecialAssetParser(AssetClass.COMMODITY).parse_wkn(soup) is None


# ---------------------------------------------------------------------------
# Helpers shared by parse_details tests
# ---------------------------------------------------------------------------

def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _stammdaten_page(rows: list[tuple[str, str]]) -> BeautifulSoup:
    row_html = "\n".join(
        f"            <tr><th scope='row'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    html = f"""
    <html><body>
      <div class="col__content">
        <p class="headline headline--h3">Stammdaten</p>
        <div class="table__container--scroll">
          <table class="simple-table">
{row_html}
          </table>
        </div>
      </div>
    </body></html>
    """
    return _make_soup(html)


# ---------------------------------------------------------------------------
# parse_details — INDEX
# ---------------------------------------------------------------------------

class TestParseDetailsIndex:
    _parser = SpecialAssetParser(AssetClass.INDEX)

    def _page(
        self,
        *,
        country: str = "DE",
        currency: str = "EUR",
        constituents: str = "40",
    ) -> BeautifulSoup:
        return _stammdaten_page([
            ("Land", country),
            ("Landeswährung", currency),
            ("Enthaltene Werte", constituents),
        ])

    def test_returns_index_details_instance(self):
        assert isinstance(self._parser.parse_details(self._page()), IndexDetails)

    def test_discriminator(self):
        assert self._parser.parse_details(self._page()).asset_class == "Index"

    def test_country(self):
        assert self._parser.parse_details(self._page(country="DE")).country == "DE"

    def test_currency(self):
        assert self._parser.parse_details(self._page(currency="EUR")).currency == "EUR"

    def test_num_constituents(self):
        assert self._parser.parse_details(self._page(constituents="40")).num_constituents == 40

    def test_num_constituents_in_anchor_tag(self):
        """Comdirect wraps the constituent count in an <a> tag — still extracts correctly."""
        soup = _stammdaten_page([
            ("Enthaltene Werte", '<a href="/inf/indizes/werte/dax-index-DE0008469008">40</a>'),
        ])
        assert self._parser.parse_details(soup).num_constituents == 40

    def test_constituents_url_built_from_isin(self):
        """constituents_url uses the ISIN from the Stammdaten table."""
        soup = _stammdaten_page([
            ("ISIN", "DE0008469008"),
            ("Enthaltene Werte", "40"),
        ])
        assert self._parser.parse_details(soup).constituents_url == "/v1/indices/DE0008469008"

    def test_constituents_url_falls_back_to_wkn(self):
        """constituents_url falls back to WKN when no ISIN is present."""
        soup = _stammdaten_page([
            ("WKN", "846900"),
            ("Enthaltene Werte", "40"),
        ])
        assert self._parser.parse_details(soup).constituents_url == "/v1/indices/846900"

    def test_constituents_url_is_none_when_no_identifier(self):
        """constituents_url is None when neither ISIN nor WKN is in the table."""
        assert self._parser.parse_details(self._page()).constituents_url is None

    def test_placeholder_becomes_none(self):
        result = self._parser.parse_details(self._page(country="--", currency="k. A."))
        assert result.country is None
        assert result.currency is None

    def test_missing_section_returns_all_none_fields(self):
        soup = _make_soup("<html><body><p>no table</p></body></html>")
        result = self._parser.parse_details(soup)
        assert isinstance(result, IndexDetails)
        assert result.country is None
        assert result.currency is None
        assert result.num_constituents is None
        assert result.constituents_url is None


# ---------------------------------------------------------------------------
# parse_details — COMMODITY
# ---------------------------------------------------------------------------

class TestParseDetailsCommodity:
    _parser = SpecialAssetParser(AssetClass.COMMODITY)

    def _page(
        self,
        *,
        currency: str = "USD",
        symbol: str = "XAU",
        country: str = "USA",
    ) -> BeautifulSoup:
        return _stammdaten_page([
            ("Land", country),
            ("Landeswährung", currency),
            ("Symbol", symbol),
        ])

    def test_returns_commodity_details_instance(self):
        assert isinstance(self._parser.parse_details(self._page()), CommodityDetails)

    def test_discriminator(self):
        assert self._parser.parse_details(self._page()).asset_class == "Commodity"

    def test_currency(self):
        assert self._parser.parse_details(self._page(currency="USD")).currency == "USD"

    def test_symbol(self):
        assert self._parser.parse_details(self._page(symbol="XAU")).symbol == "XAU"

    def test_country(self):
        assert self._parser.parse_details(self._page(country="USA")).country == "USA"

    def test_country_placeholder_becomes_none(self):
        assert self._parser.parse_details(self._page(country="--")).country is None

    def test_missing_section_returns_all_none_fields(self):
        soup = _make_soup("<html><body><p>no table</p></body></html>")
        result = self._parser.parse_details(soup)
        assert isinstance(result, CommodityDetails)
        assert result.currency is None
        assert result.symbol is None
        assert result.country is None


# ---------------------------------------------------------------------------
# parse_details — CURRENCY
# ---------------------------------------------------------------------------

class TestParseDetailsCurrency:
    _parser = SpecialAssetParser(AssetClass.CURRENCY)

    def _page(
        self,
        *,
        exchange_rate: str = "EUR/USD",
        country: str = "USA",
    ) -> BeautifulSoup:
        return _stammdaten_page([
            ("Land", country),
            ("Wechselkurs", exchange_rate),
        ])

    def test_returns_currency_details_instance(self):
        assert isinstance(self._parser.parse_details(self._page()), CurrencyDetails)

    def test_discriminator(self):
        assert self._parser.parse_details(self._page()).asset_class == "Currency"

    def test_base_currency_parsed_from_exchange_rate(self):
        assert self._parser.parse_details(self._page(exchange_rate="EUR/USD")).base_currency == "EUR"

    def test_quote_currency_parsed_from_exchange_rate(self):
        assert self._parser.parse_details(self._page(exchange_rate="EUR/USD")).quote_currency == "USD"

    def test_country(self):
        assert self._parser.parse_details(self._page(country="USA")).country == "USA"

    def test_gbp_usd_pair(self):
        result = self._parser.parse_details(self._page(exchange_rate="GBP/USD"))
        assert result.base_currency == "GBP"
        assert result.quote_currency == "USD"

    def test_exchange_rate_placeholder_yields_none_currencies(self):
        result = self._parser.parse_details(self._page(exchange_rate="--"))
        assert result.base_currency is None
        assert result.quote_currency is None

    def test_country_placeholder_becomes_none(self):
        assert self._parser.parse_details(self._page(country="--")).country is None

    def test_missing_section_returns_all_none_fields(self):
        soup = _make_soup("<html><body><p>no table</p></body></html>")
        result = self._parser.parse_details(soup)
        assert isinstance(result, CurrencyDetails)
        assert result.base_currency is None
        assert result.quote_currency is None
        assert result.country is None


# ---------------------------------------------------------------------------
# parse_details — dispatch (unknown asset class returns None)
# ---------------------------------------------------------------------------

class TestParseDetailsDispatch:
    def test_returns_none_for_non_special_asset_class(self):
        # Force an invalid state by bypassing __init__ validation
        parser = SpecialAssetParser(AssetClass.INDEX)
        parser._asset_class = AssetClass.STOCK  # type: ignore[assignment]
        assert parser.parse_details(_make_soup("<html><body></body></html>")) is None

