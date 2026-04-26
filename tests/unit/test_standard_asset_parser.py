"""
Unit tests for StandardAssetParser.parse_details — all five standard asset classes.

Covers:
- ``clean_float_value``          — German decimal string → float
- ``clean_numeric_value``        — German integer/magnitude string → int (incl. Bil.)
- ``StandardAssetParser.parse_details`` for:
    - STOCK  (Aktieninformationen)
    - BOND   (Anleiheinformationen)
    - ETF    (ETF-Informationen)
    - FONDS  (Fondsinformationen)
    - CERTIFICATE (Zertifikatinformationen)
- ``InstrumentDetails`` discriminated union round-trip serialisation
"""

import textwrap
from datetime import date

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
# Shared helpers
# ---------------------------------------------------------------------------


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _section_page(section_header: str, rows: list[tuple[str, str]]) -> BeautifulSoup:
    """Build a minimal page with one Stammdaten-style table under a <p> header."""
    row_html = "\n".join(
        f"            <tr><th scope='row'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    html = f"""
    <html><body>
      <div class="col__content">
        <p class="headline headline--h3">{section_header}</p>
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


class TestCleanNumericValue:
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
# STOCK
# ---------------------------------------------------------------------------


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


_stock_parser = StandardAssetParser(AssetClass.STOCK)


class TestStockDetailsParser:
    def test_returns_stock_details_instance(self):
        assert isinstance(_stock_parser.parse_details(_stock_page()), StockDetails)

    def test_discriminator(self):
        assert _stock_parser.parse_details(_stock_page()).asset_class == "Stock"

    def test_security_type(self):
        assert _stock_parser.parse_details(_stock_page(wertpapiertyp="Stammaktie")).security_type == "Stammaktie"

    def test_market_segment(self):
        assert _stock_parser.parse_details(_stock_page(marktsegment="Freiverkehr")).market_segment == "Freiverkehr"

    def test_sector_from_span_title(self):
        """Sector must come from the span title attribute, not the truncated display text."""
        result = _stock_parser.parse_details(
            _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        )
        assert result.sector == "Halbleiterindustrie"

    def test_sector_not_truncated(self):
        result = _stock_parser.parse_details(
            _stock_page(branche_title="Halbleiterindustrie", branche_display="Halbleiterind..")
        )
        assert result.sector != "Halbleiterind.."

    def test_fiscal_year_end_normalised(self):
        assert _stock_parser.parse_details(_stock_page(geschaeftsjahr="25.01.")).fiscal_year_end == "25-01"

    def test_fiscal_year_end_december(self):
        assert _stock_parser.parse_details(_stock_page(geschaeftsjahr="31.12.")).fiscal_year_end == "31-12"

    def test_fiscal_year_end_placeholder(self):
        assert _stock_parser.parse_details(_stock_page(geschaeftsjahr="--")).fiscal_year_end is None

    def test_market_cap_bil(self):
        """4,20 Bil. EUR → 4.2 × 10^12 (German Billion = English Trillion)."""
        result = _stock_parser.parse_details(_stock_page(marktkapital="4,20 Bil. EUR"))
        assert result.market_cap == pytest.approx(4_200_000_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mrd(self):
        result = _stock_parser.parse_details(_stock_page(marktkapital="3,10 Mrd. EUR"))
        assert result.market_cap == pytest.approx(3_100_000_000.0)
        assert result.market_cap_currency == "EUR"

    def test_market_cap_mio_usd(self):
        result = _stock_parser.parse_details(_stock_page(marktkapital="512,00 Mio. USD"))
        assert result.market_cap == pytest.approx(512_000_000.0)
        assert result.market_cap_currency == "USD"

    def test_market_cap_placeholder(self):
        result = _stock_parser.parse_details(_stock_page(marktkapital="--"))
        assert result.market_cap is None
        assert result.market_cap_currency is None

    def test_free_float(self):
        assert _stock_parser.parse_details(_stock_page(streubesitz="68,46 %")).free_float == pytest.approx(68.46)

    def test_free_float_placeholder(self):
        assert _stock_parser.parse_details(_stock_page(streubesitz="--")).free_float is None

    def test_nominal_value_and_currency(self):
        result = _stock_parser.parse_details(_stock_page(nennwert="0,00 USD"))
        assert result.nominal_value == pytest.approx(0.0)
        assert result.nominal_value_currency == "USD"

    def test_nominal_value_placeholder(self):
        result = _stock_parser.parse_details(_stock_page(nennwert="--"))
        assert result.nominal_value is None
        assert result.nominal_value_currency is None

    def test_shares_outstanding_mrd(self):
        result = _stock_parser.parse_details(_stock_page(stuecke="24,30 Mrd."))
        assert result.shares_outstanding == pytest.approx(24_300_000_000.0)

    def test_shares_outstanding_plain(self):
        result = _stock_parser.parse_details(_stock_page(stuecke="24.800.000"))
        assert result.shares_outstanding == pytest.approx(24_800_000.0)

    def test_shares_outstanding_placeholder(self):
        assert _stock_parser.parse_details(_stock_page(stuecke="--")).shares_outstanding is None

    def test_missing_section_returns_empty_stock_details(self):
        soup = _make_soup("<html><body><p>No data</p></body></html>")
        result = _stock_parser.parse_details(soup)
        assert isinstance(result, StockDetails)
        assert result.sector is None
        assert result.market_cap is None


# ---------------------------------------------------------------------------
# BOND
# ---------------------------------------------------------------------------


def _bond_page(
    *,
    emittent: str = "Bundesrepublik Deutschland",
    zinssatz: str = "4,50 %",
    zinsart: str = "Fest",
    ausgabedatum: str = "15.01.2020",
    faelligkeit: str = "15.01.2030",
    nennwert: str = "1.000,00 EUR",
    anleihetyp: str = "Staatsanleihe",
    moodys: str = "Aaa",
    sp: str = "AAA",
    waehrung: str = "EUR",
) -> BeautifulSoup:
    return _section_page("Anleiheinformationen", [
        ("Emittent", emittent),
        ("Zinssatz", zinssatz),
        ("Zinsart", zinsart),
        ("Ausgabedatum", ausgabedatum),
        ("Fälligkeit", faelligkeit),
        ("Nennwert", nennwert),
        ("Anleihetyp", anleihetyp),
        ("Moody's", moodys),
        ("S&P", sp),
        ("Währung", waehrung),
    ])


_bond_parser = StandardAssetParser(AssetClass.BOND)


class TestBondDetailsParser:
    def test_returns_bond_details_instance(self):
        assert isinstance(_bond_parser.parse_details(_bond_page()), BondDetails)

    def test_discriminator(self):
        assert _bond_parser.parse_details(_bond_page()).asset_class == "Bond"

    def test_issuer(self):
        assert _bond_parser.parse_details(_bond_page(emittent="Bundesrepublik Deutschland")).issuer == "Bundesrepublik Deutschland"

    def test_coupon_rate(self):
        assert _bond_parser.parse_details(_bond_page(zinssatz="4,50 %")).coupon_rate == pytest.approx(4.50)

    def test_coupon_type(self):
        assert _bond_parser.parse_details(_bond_page(zinsart="Fest")).coupon_type == "Fest"

    def test_issue_date(self):
        assert _bond_parser.parse_details(_bond_page(ausgabedatum="15.01.2020")).issue_date == date(2020, 1, 15)

    def test_maturity_date(self):
        assert _bond_parser.parse_details(_bond_page(faelligkeit="15.01.2030")).maturity_date == date(2030, 1, 15)

    def test_nominal_value_with_currency(self):
        assert _bond_parser.parse_details(_bond_page(nennwert="1.000,00 EUR")).nominal_value == pytest.approx(1000.0)

    def test_bond_type(self):
        assert _bond_parser.parse_details(_bond_page(anleihetyp="Staatsanleihe")).bond_type == "Staatsanleihe"

    def test_credit_rating_moodys(self):
        assert _bond_parser.parse_details(_bond_page(moodys="Aaa")).credit_rating_moodys == "Aaa"

    def test_credit_rating_sp(self):
        assert _bond_parser.parse_details(_bond_page(sp="AAA")).credit_rating_sp == "AAA"

    def test_currency(self):
        assert _bond_parser.parse_details(_bond_page(waehrung="EUR")).currency == "EUR"

    def test_placeholder_dash_becomes_none(self):
        result = _bond_parser.parse_details(_bond_page(emittent="--", moodys="--", sp="--", zinssatz="--"))
        assert result.issuer is None
        assert result.coupon_rate is None
        assert result.credit_rating_moodys is None
        assert result.credit_rating_sp is None

    def test_missing_section_returns_empty_bond_details(self):
        result = _bond_parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, BondDetails)
        assert result.issuer is None
        assert result.maturity_date is None

    def test_two_digit_year_date(self):
        assert _bond_parser.parse_details(_bond_page(faelligkeit="15.01.30")).maturity_date == date(2030, 1, 15)

    def test_invalid_date_becomes_none(self):
        assert _bond_parser.parse_details(_bond_page(faelligkeit="Open End")).maturity_date is None


# ---------------------------------------------------------------------------
# ETF
# ---------------------------------------------------------------------------


def _etf_page(
    *,
    index: str = "MSCI World",
    ter: str = "0,20 %",
    replication: str = "physisch",
    distribution: str = "thesaurierend",
    domicile: str = "Irland",
    inception: str = "25.10.2005",
    currency: str = "USD",
    fund_size: str = "1,23 Mrd.",
) -> BeautifulSoup:
    return _section_page("ETF-Informationen", [
        ("Abgebildeter Index", index),
        ("TER", ter),
        ("Replikationsmethode", replication),
        ("Ausschüttungsart", distribution),
        ("Fondsdomizil", domicile),
        ("Auflagedatum", inception),
        ("Fondswährung", currency),
        ("Fondsvermögen", fund_size),
    ])


_etf_parser = StandardAssetParser(AssetClass.ETF)


class TestETFDetailsParser:
    def test_returns_etf_details_instance(self):
        assert isinstance(_etf_parser.parse_details(_etf_page()), ETFDetails)

    def test_discriminator(self):
        assert _etf_parser.parse_details(_etf_page()).asset_class == "ETF"

    def test_tracked_index(self):
        assert _etf_parser.parse_details(_etf_page(index="MSCI World")).tracked_index == "MSCI World"

    def test_expense_ratio(self):
        assert _etf_parser.parse_details(_etf_page(ter="0,20 %")).expense_ratio == pytest.approx(0.20)

    def test_replication_method(self):
        assert _etf_parser.parse_details(_etf_page(replication="physisch")).replication_method == "physisch"

    def test_distribution_policy(self):
        assert _etf_parser.parse_details(_etf_page(distribution="thesaurierend")).distribution_policy == "thesaurierend"

    def test_fund_domicile(self):
        assert _etf_parser.parse_details(_etf_page(domicile="Irland")).fund_domicile == "Irland"

    def test_inception_date(self):
        assert _etf_parser.parse_details(_etf_page(inception="25.10.2005")).inception_date == date(2005, 10, 25)

    def test_fund_currency(self):
        assert _etf_parser.parse_details(_etf_page(currency="USD")).fund_currency == "USD"

    def test_fund_size_mrd(self):
        assert _etf_parser.parse_details(_etf_page(fund_size="1,23 Mrd.")).fund_size == pytest.approx(1_230_000_000.0)

    def test_fund_size_mio(self):
        assert _etf_parser.parse_details(_etf_page(fund_size="512,00 Mio.")).fund_size == pytest.approx(512_000_000.0)

    def test_fund_size_placeholder(self):
        assert _etf_parser.parse_details(_etf_page(fund_size="--")).fund_size is None

    def test_placeholder_becomes_none(self):
        result = _etf_parser.parse_details(_etf_page(index="--", replication="--"))
        assert result.tracked_index is None
        assert result.replication_method is None

    def test_missing_section_returns_empty_etf_details(self):
        result = _etf_parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, ETFDetails)
        assert result.tracked_index is None


# ---------------------------------------------------------------------------
# FONDS
# ---------------------------------------------------------------------------


def _fonds_page(
    *,
    fund_type: str = "Aktienfonds",
    fund_manager: str = "BlackRock",
    inception: str = "01.04.1994",
    domicile: str = "Luxemburg",
    distribution: str = "ausschüttend",
    ter: str = "1,50 %",
    currency: str = "EUR",
    fund_size: str = "512,00 Mio.",
) -> BeautifulSoup:
    return _section_page("Fondsinformationen", [
        ("Fondstyp", fund_type),
        ("Fondsmanager", fund_manager),
        ("Auflagedatum", inception),
        ("Fondsdomizil", domicile),
        ("Ausschüttungsart", distribution),
        ("TER", ter),
        ("Fondswährung", currency),
        ("Fondsvermögen", fund_size),
    ])


_fonds_parser = StandardAssetParser(AssetClass.FONDS)


class TestFondsDetailsParser:
    def test_returns_fonds_details_instance(self):
        assert isinstance(_fonds_parser.parse_details(_fonds_page()), FondsDetails)

    def test_discriminator(self):
        assert _fonds_parser.parse_details(_fonds_page()).asset_class == "Fund"

    def test_fund_type(self):
        assert _fonds_parser.parse_details(_fonds_page(fund_type="Aktienfonds")).fund_type == "Aktienfonds"

    def test_fund_manager(self):
        assert _fonds_parser.parse_details(_fonds_page(fund_manager="BlackRock")).fund_manager == "BlackRock"

    def test_inception_date(self):
        assert _fonds_parser.parse_details(_fonds_page(inception="01.04.1994")).inception_date == date(1994, 4, 1)

    def test_fund_domicile(self):
        assert _fonds_parser.parse_details(_fonds_page(domicile="Luxemburg")).fund_domicile == "Luxemburg"

    def test_distribution_policy(self):
        assert _fonds_parser.parse_details(_fonds_page(distribution="ausschüttend")).distribution_policy == "ausschüttend"

    def test_expense_ratio(self):
        assert _fonds_parser.parse_details(_fonds_page(ter="1,50 %")).expense_ratio == pytest.approx(1.50)

    def test_fund_currency(self):
        assert _fonds_parser.parse_details(_fonds_page(currency="EUR")).fund_currency == "EUR"

    def test_fund_size_mio(self):
        assert _fonds_parser.parse_details(_fonds_page(fund_size="512,00 Mio.")).fund_size == pytest.approx(512_000_000.0)

    def test_fund_size_mrd(self):
        assert _fonds_parser.parse_details(_fonds_page(fund_size="3,10 Mrd.")).fund_size == pytest.approx(3_100_000_000.0)

    def test_placeholder_becomes_none(self):
        result = _fonds_parser.parse_details(_fonds_page(fund_type="--", fund_manager="--"))
        assert result.fund_type is None
        assert result.fund_manager is None

    def test_missing_section_returns_empty_fonds_details(self):
        result = _fonds_parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, FondsDetails)
        assert result.fund_type is None


# ---------------------------------------------------------------------------
# CERTIFICATE
# ---------------------------------------------------------------------------


def _certificate_page(
    *,
    cert_type: str = "Discount",
    basiswert: str = "DAX",
    cap: str = "18.000,00 EUR",
    barrier: str = "14.000,00 EUR",
    participation: str = "100,00 %",
    faelligkeit: str = "20.12.2025",
    emittent: str = "DZ BANK AG",
    waehrung: str = "EUR",
) -> BeautifulSoup:
    return _section_page("Zertifikatinformationen", [
        ("Zertifikattyp", cert_type),
        ("Basiswert", basiswert),
        ("Cap-Niveau", cap),
        ("Barriere", barrier),
        ("Partizipationsrate", participation),
        ("Fälligkeit", faelligkeit),
        ("Emittent", emittent),
        ("Währung", waehrung),
    ])


_cert_parser = StandardAssetParser(AssetClass.CERTIFICATE)


class TestCertificateDetailsParser:
    def test_returns_certificate_details_instance(self):
        assert isinstance(_cert_parser.parse_details(_certificate_page()), CertificateDetails)

    def test_discriminator(self):
        assert _cert_parser.parse_details(_certificate_page()).asset_class == "Certificate"

    def test_certificate_type(self):
        assert _cert_parser.parse_details(_certificate_page(cert_type="Discount")).certificate_type == "Discount"

    def test_underlying_name(self):
        assert _cert_parser.parse_details(_certificate_page(basiswert="DAX")).underlying_name == "DAX"

    def test_cap_value_and_currency(self):
        result = _cert_parser.parse_details(_certificate_page(cap="18.000,00 EUR"))
        assert result.cap == pytest.approx(18_000.0)
        assert result.cap_currency == "EUR"

    def test_barrier_value_and_currency(self):
        result = _cert_parser.parse_details(_certificate_page(barrier="14.000,00 EUR"))
        assert result.barrier == pytest.approx(14_000.0)
        assert result.barrier_currency == "EUR"

    def test_participation_rate(self):
        assert _cert_parser.parse_details(_certificate_page(participation="100,00 %")).participation_rate == pytest.approx(100.0)

    def test_maturity_date(self):
        assert _cert_parser.parse_details(_certificate_page(faelligkeit="20.12.2025")).maturity_date == date(2025, 12, 20)

    def test_open_end_maturity_is_none(self):
        assert _cert_parser.parse_details(_certificate_page(faelligkeit="Open End")).maturity_date is None

    def test_issuer(self):
        assert _cert_parser.parse_details(_certificate_page(emittent="DZ BANK AG")).issuer == "DZ BANK AG"

    def test_currency(self):
        assert _cert_parser.parse_details(_certificate_page(waehrung="EUR")).currency == "EUR"

    def test_placeholder_cap_becomes_none(self):
        result = _cert_parser.parse_details(_certificate_page(cap="--", barrier="--"))
        assert result.cap is None
        assert result.cap_currency is None
        assert result.barrier is None
        assert result.barrier_currency is None

    def test_missing_section_returns_empty_certificate_details(self):
        result = _cert_parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, CertificateDetails)
        assert result.certificate_type is None
        assert result.maturity_date is None

    def test_no_cap_barrier_for_tracker(self):
        result = _cert_parser.parse_details(_certificate_page(cert_type="Tracker", cap="--", barrier="--"))
        assert result.cap is None
        assert result.barrier is None


# ---------------------------------------------------------------------------
# parse_details dispatch — unregistered asset classes return None
# ---------------------------------------------------------------------------


class TestParseDetailsDispatch:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.BOND,
        AssetClass.ETF,
        AssetClass.FONDS,
        AssetClass.CERTIFICATE,
    ])
    def test_returns_detail_object_not_none(self, asset_class):
        """Bond/ETF/Fonds/Certificate parsers return a details object (not None)."""
        parser = StandardAssetParser(asset_class)
        assert parser.parse_details(_stock_page()) is not None

    def test_index_returns_none(self):
        """INDEX is handled by SpecialAssetParser — StandardAssetParser returns None."""
        assert StandardAssetParser(AssetClass.INDEX).parse_details(_stock_page()) is None


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
        details = BondDetails(issuer="Bund", coupon_rate=1.5, maturity_date=date(2030, 1, 15))
        data = details.model_dump()
        assert data["asset_class"] == "Bond"
        assert data["coupon_rate"] == pytest.approx(1.5)
        assert data["maturity_date"] == date(2030, 1, 15)

    def test_optional_fields_default_to_none(self):
        details = ETFDetails()
        assert details.tracked_index is None
        assert details.expense_ratio is None
