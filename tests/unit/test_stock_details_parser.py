"""
Unit tests for stock-details parsing.

Covers:
- ``clean_float_value``          — German decimal string → float
- ``clean_numeric_value``        — German integer/magnitude string → int (incl. Bil.)
- ``StandardAssetParser.parse_details``
    - Full stock page: all Aktieninformationen fields extracted correctly
    - Branche span-title extraction (truncated display text is ignored)
    - Market cap with Bil./Mrd./Mio. suffix and currency suffix
    - Fiscal year end "DD.MM." is normalised to "MM-DD"
    - Nennwert split into value + currency
    - Missing / "--" fields become None
    - Non-STOCK asset classes return None from parse_details
- ``InstrumentDetails`` discriminated union round-trip
"""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import (
    BondDetails,
    CertificateDetails,
    CommodityDetails,
    CurrencyDetails,
    ETFDetails,
    FondsDetails,
    IndexDetails,
    StockDetails,
    WarrantDetails,
)
from app.models.instruments import AssetClass
from app.parsers.plugins.parsing_utils import clean_float_value, clean_numeric_value
from app.parsers.plugins.standard_asset_parser import StandardAssetParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# clean_float_value
# ---------------------------------------------------------------------------

class TestCleanFloatValue:
    def test_german_decimal_with_percent(self):
        assert clean_float_value("2,34 %") == pytest.approx(2.34)

    def test_german_decimal_no_percent(self):
        assert clean_float_value("2,34") == pytest.approx(2.34)

    def test_german_thousand_and_decimal(self):
        assert clean_float_value("1.234,56") == pytest.approx(1234.56)

    def test_plain_dot_decimal(self):
        assert clean_float_value("3.14") == pytest.approx(3.14)

    def test_placeholder_dash(self):
        assert clean_float_value("--") is None

    def test_single_dash(self):
        assert clean_float_value("-") is None

    def test_empty_string(self):
        assert clean_float_value("") is None

    def test_none_value(self):
        assert clean_float_value(None) is None  # type: ignore[arg-type]

    def test_zero(self):
        assert clean_float_value("0,00 %") == pytest.approx(0.0)

    def test_whitespace_only(self):
        assert clean_float_value("   ") is None


# ---------------------------------------------------------------------------
# clean_numeric_value — including Bil. (German trillion = 10^12)
# ---------------------------------------------------------------------------

class TestCleanNumericValueBil:
    def test_bil_suffix(self):
        assert clean_numeric_value("4,20 Bil.") == 4_200_000_000_000

    def test_mrd_suffix(self):
        assert clean_numeric_value("3,10 Mrd.") == 3_100_000_000

    def test_mio_suffix(self):
        assert clean_numeric_value("512,00 Mio.") == 512_000_000

    def test_plain_integer(self):
        assert clean_numeric_value("24.800.000") == 24_800_000

    def test_placeholder(self):
        assert clean_numeric_value("--") is None


# ---------------------------------------------------------------------------
# StandardAssetParser.parse_details — STOCK
# ---------------------------------------------------------------------------

class TestStockDetailsParser:
    parser = StandardAssetParser(AssetClass.STOCK)

    def test_returns_stock_details_instance(self):
        soup = _stock_page()
        result = self.parser.parse_details(soup)
        assert isinstance(result, StockDetails)

    def test_discriminator_field(self):
        soup = _stock_page()
        result = self.parser.parse_details(soup)
        assert result.asset_class == "Stock"

    def test_security_type(self):
        soup = _stock_page(wertpapiertyp="Stammaktie")
        assert self.parser.parse_details(soup).security_type == "Stammaktie"

    def test_market_segment(self):
        soup = _stock_page(marktsegment="Freiverkehr")
        assert self.parser.parse_details(soup).market_segment == "Freiverkehr"

    def test_sector_from_span_title(self):
        """Sector must come from the span title attribute, not the truncated display text."""
        soup = _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        result = self.parser.parse_details(soup)
        assert result.sector == "Halbleiterindustrie"

    def test_sector_not_truncated(self):
        """Truncated display text must not appear in the result."""
        soup = _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        assert self.parser.parse_details(soup).sector != "Halbleiterind.."

    def test_fiscal_year_end_normalised(self):
        soup = _stock_page(geschaeftsjahr="25.01.")
        result = self.parser.parse_details(soup)
        assert result.fiscal_year_end == "25-01"

    def test_fiscal_year_end_december(self):
        soup = _stock_page(geschaeftsjahr="31.12.")
        result = self.parser.parse_details(soup)
        assert result.fiscal_year_end == "31-12"

    def test_fiscal_year_end_placeholder(self):
        soup = _stock_page(geschaeftsjahr="--")
        result = self.parser.parse_details(soup)
        assert result.fiscal_year_end is None

    def test_market_cap_bil(self):
        """4,20 Bil. EUR → 4.2 × 10^12 (German Billion = English Trillion)."""
        soup = _stock_page(marktkapital="4,20 Bil. EUR")
        result = self.parser.parse_details(soup)
        assert result.market_cap == pytest.approx(4_200_000_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mrd(self):
        soup = _stock_page(marktkapital="3,10 Mrd. EUR")
        result = self.parser.parse_details(soup)
        assert result.market_cap == pytest.approx(3_100_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mio_usd(self):
        soup = _stock_page(marktkapital="512,00 Mio. USD")
        result = self.parser.parse_details(soup)
        assert result.market_cap == pytest.approx(512_000_000.0)
        assert result.market_cap_currency == "USD"

    def test_market_cap_placeholder(self):
        soup = _stock_page(marktkapital="--")
        result = self.parser.parse_details(soup)
        assert result.market_cap is None
        assert result.market_cap_currency is None

    def test_free_float(self):
        soup = _stock_page(streubesitz="68,46 %")
        result = self.parser.parse_details(soup)
        assert result.free_float == pytest.approx(68.46)

    def test_free_float_placeholder(self):
        soup = _stock_page(streubesitz="--")
        result = self.parser.parse_details(soup)
        assert result.free_float is None

    def test_nominal_value_and_currency(self):
        soup = _stock_page(nennwert="0,00 USD")
        result = self.parser.parse_details(soup)
        assert result.nominal_value == pytest.approx(0.0)
        assert result.nominal_value_currency == "USD"

    def test_nominal_value_placeholder(self):
        soup = _stock_page(nennwert="--")
        result = self.parser.parse_details(soup)
        assert result.nominal_value is None
        assert result.nominal_value_currency is None

    def test_shares_outstanding_mrd(self):
        soup = _stock_page(stuecke="24,30 Mrd.")
        result = self.parser.parse_details(soup)
        assert result.shares_outstanding == pytest.approx(24_300_000_000.0)

    def test_shares_outstanding_plain(self):
        soup = _stock_page(stuecke="24.800.000")
        result = self.parser.parse_details(soup)
        assert result.shares_outstanding == pytest.approx(24_800_000.0)

    def test_shares_outstanding_placeholder(self):
        soup = _stock_page(stuecke="--")
        result = self.parser.parse_details(soup)
        assert result.shares_outstanding is None

    def test_missing_aktieninformationen_section_returns_empty_stock_details(self):
        """When the Aktieninformationen section is absent, all fields are None."""
        soup = _make_soup("<html><body><p>No data</p></body></html>")
        result = self.parser.parse_details(soup)
        assert isinstance(result, StockDetails)
        assert result.sector is None
        assert result.market_cap is None


# ---------------------------------------------------------------------------
# parse_details returns None for non-STOCK asset classes
# ---------------------------------------------------------------------------

class TestParseDetailsNonStock:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.BOND,
        AssetClass.ETF,
        AssetClass.FONDS,
        AssetClass.CERTIFICATE,
    ])
    def test_returns_none_for_non_stock(self, asset_class):
        parser = StandardAssetParser(asset_class)
        soup = _stock_page()  # content doesn't matter — should short-circuit
        assert parser.parse_details(soup) is None


# ---------------------------------------------------------------------------
# InstrumentDetails discriminated union — round-trip serialisation
# ---------------------------------------------------------------------------

class TestInstrumentDetailsUnion:
    """Ensure each concrete model carries the correct discriminator literal."""

    @pytest.mark.parametrize("model,expected", [
        (StockDetails(),       "Stock"),
        (BondDetails(),        "Bond"),
        (ETFDetails(),         "ETF"),
        (FondsDetails(),       "Fund"),
        (WarrantDetails(),     "Warrant"),
        (CertificateDetails(), "Certificate"),
        (IndexDetails(),       "Index"),
        (CommodityDetails(),   "Commodity"),
        (CurrencyDetails(),    "Currency"),
    ])
    def test_discriminator_value(self, model, expected):
        assert model.asset_class == expected

    def test_stock_details_serialises_to_dict(self):
        details = StockDetails(sector="Halbleiterindustrie", free_float=68.46)
        data = details.model_dump()
        assert data["asset_class"] == "Stock"
        assert data["sector"] == "Halbleiterindustrie"
        assert data["free_float"] == pytest.approx(68.46)

    def test_bond_details_serialises_to_dict(self):
        from datetime import date
        details = BondDetails(issuer="Bund", coupon_rate=1.5, maturity_date=date(2030, 1, 15))
        data = details.model_dump()
        assert data["asset_class"] == "Bond"
        assert data["coupon_rate"] == pytest.approx(1.5)
        assert data["maturity_date"] == date(2030, 1, 15)

    def test_optional_fields_default_to_none(self):
        details = ETFDetails()
        assert details.tracked_index is None
        assert details.expense_ratio is None
