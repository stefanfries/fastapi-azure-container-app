"""Unit tests for app.parsers.plugins.stock_parser.StockParser."""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import StockDetails
from app.parsers.plugins.stock_parser import StockParser


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _stock_page(
    *,
    wertpapiertyp: str = "Stammaktie",
    marktsegment: str = "Freiverkehr",
    branche_title: str = "Halbleiterindustrie",
    branche_display: str = "Halbleiterind..",
    geschaeftsjahr: str = "25.01.",
    marktkapital: str = "4,20 Bil. EUR",
    streubesitz: str = "68,46 %",
    nennwert: str = "0,00 USD",
    stuecke: str = "24,30 Mrd.",
) -> BeautifulSoup:
    """Return a minimal BeautifulSoup page matching the real comdirect Aktieninformationen HTML."""
    html = f"""
    <html><body>
      <div class="col__content col__content--no-padding">
        <p class="headline headline--h3">Aktieninformationen</p>
        <div class="table__container--scroll">
          <table class="simple-table">
            <tr><th scope="row">Wertpapiertyp</th><td>{wertpapiertyp}</td></tr>
            <tr><th scope="row">Marktsegment</th><td>{marktsegment}</td></tr>
            <tr><th scope="row">Branche</th><td><span title="{branche_title}">{branche_display}</span></td></tr>
            <tr><th scope="row">Geschäftsjahr</th><td>{geschaeftsjahr}</td></tr>
            <tr><th scope="row">Marktkapital.</th><td>{marktkapital}</td></tr>
            <tr><th scope="row">Streubesitz</th><td>{streubesitz}</td></tr>
            <tr><th scope="row">Nennwert</th><td>{nennwert}</td></tr>
            <tr><th scope="row">Stücke</th><td>{stuecke}</td></tr>
          </table>
        </div>
      </div>
    </body></html>
    """
    return _make_soup(html)


_parser = StockParser()


class TestStockDetailsParser:
    def test_returns_stock_details_instance(self):
        assert isinstance(_parser.parse_details(_stock_page()), StockDetails)

    def test_discriminator(self):
        assert _parser.parse_details(_stock_page()).asset_class == "Stock"

    def test_security_type(self):
        assert _parser.parse_details(_stock_page(wertpapiertyp="Stammaktie")).security_type == "Stammaktie"

    def test_market_segment(self):
        assert _parser.parse_details(_stock_page(marktsegment="Freiverkehr")).market_segment == "Freiverkehr"

    def test_sector_from_span_title(self):
        """Sector must come from the span title attribute, not the truncated display text."""
        result = _parser.parse_details(
            _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        )
        assert result.sector == "Halbleiterindustrie"

    def test_sector_not_truncated(self):
        result = _parser.parse_details(
            _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        )
        assert result.sector != "Halbleiterind.."

    def test_fiscal_year_end_normalised(self):
        assert _parser.parse_details(_stock_page(geschaeftsjahr="25.01.")).fiscal_year_end == "25-01"

    def test_fiscal_year_end_december(self):
        assert _parser.parse_details(_stock_page(geschaeftsjahr="31.12.")).fiscal_year_end == "31-12"

    def test_fiscal_year_end_placeholder(self):
        assert _parser.parse_details(_stock_page(geschaeftsjahr="--")).fiscal_year_end is None

    def test_market_cap_bil(self):
        """4,20 Bil. EUR → 4.2 × 10^12 (German Billion = English Trillion)."""
        result = _parser.parse_details(_stock_page(marktkapital="4,20 Bil. EUR"))
        assert result.market_cap == pytest.approx(4_200_000_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mrd(self):
        result = _parser.parse_details(_stock_page(marktkapital="3,10 Mrd. EUR"))
        assert result.market_cap == pytest.approx(3_100_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mio_usd(self):
        result = _parser.parse_details(_stock_page(marktkapital="512,00 Mio. USD"))
        assert result.market_cap == pytest.approx(512_000_000.0)
        assert result.market_cap_currency == "USD"

    def test_market_cap_placeholder(self):
        result = _parser.parse_details(_stock_page(marktkapital="--"))
        assert result.market_cap is None
        assert result.market_cap_currency is None

    def test_free_float(self):
        assert _parser.parse_details(_stock_page(streubesitz="68,46 %")).free_float == pytest.approx(68.46)

    def test_free_float_placeholder(self):
        assert _parser.parse_details(_stock_page(streubesitz="--")).free_float is None

    def test_nominal_value_and_currency(self):
        result = _parser.parse_details(_stock_page(nennwert="0,00 USD"))
        assert result.nominal_value == pytest.approx(0.0)
        assert result.nominal_value_currency == "USD"

    def test_nominal_value_placeholder(self):
        result = _parser.parse_details(_stock_page(nennwert="--"))
        assert result.nominal_value is None
        assert result.nominal_value_currency is None

    def test_shares_outstanding_mrd(self):
        result = _parser.parse_details(_stock_page(stuecke="24,30 Mrd."))
        assert result.shares_outstanding == pytest.approx(24_300_000_000.0)

    def test_shares_outstanding_plain(self):
        result = _parser.parse_details(_stock_page(stuecke="24.800.000"))
        assert result.shares_outstanding == pytest.approx(24_800_000.0)

    def test_shares_outstanding_placeholder(self):
        assert _parser.parse_details(_stock_page(stuecke="--")).shares_outstanding is None

    def test_missing_section_returns_empty_stock_details(self):
        soup = _make_soup("<html><body><p>No data</p></body></html>")
        result = _parser.parse_details(soup)
        assert isinstance(result, StockDetails)
        assert result.sector is None
        assert result.market_cap is None
