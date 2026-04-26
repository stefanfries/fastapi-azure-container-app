"""Unit tests for app.parsers.plugins.bond_parser.BondParser."""

import textwrap
from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import BondDetails
from app.parsers.plugins.bond_parser import BondParser


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _section_page(section_header: str, rows: list[tuple[str, str]]) -> BeautifulSoup:
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
    return _section_page("Stammdaten", [
        ("Emittent", emittent),
        ("Nominalzinssatz", zinssatz),
        ("Kupon-Art", zinsart),
        ("Ausgabedatum", ausgabedatum),
        ("F\u00e4lligkeit", faelligkeit),
        ("St\u00fcckelung", nennwert),
        ("Typ", anleihetyp),
        ("Moody's", moodys),
        ("S&P", sp),
        ("Währung", waehrung),
    ])


_parser = BondParser()


class TestBondDetailsParser:
    def test_returns_bond_details_instance(self):
        assert isinstance(_parser.parse_details(_bond_page()), BondDetails)

    def test_discriminator(self):
        assert _parser.parse_details(_bond_page()).asset_class == "Bond"

    def test_issuer(self):
        assert _parser.parse_details(_bond_page(emittent="Bundesrepublik Deutschland")).issuer == "Bundesrepublik Deutschland"

    def test_coupon_rate(self):
        assert _parser.parse_details(_bond_page(zinssatz="4,50 %")).coupon_rate_percent == pytest.approx(4.50)

    def test_coupon_type(self):
        assert _parser.parse_details(_bond_page(zinsart="Fest")).coupon_type == "Fest"

    def test_issue_date(self):
        assert _parser.parse_details(_bond_page(ausgabedatum="15.01.2020")).issue_date == date(2020, 1, 15)

    def test_maturity_date(self):
        assert _parser.parse_details(_bond_page(faelligkeit="15.01.2030")).maturity_date == date(2030, 1, 15)

    def test_nominal_value_with_currency(self):
        assert _parser.parse_details(_bond_page(nennwert="1.000,00 EUR")).nominal_value == pytest.approx(1000.0)

    def test_bond_type(self):
        assert _parser.parse_details(_bond_page(anleihetyp="Staatsanleihe")).bond_type == "Staatsanleihe"

    def test_currency(self):
        assert _parser.parse_details(_bond_page(waehrung="EUR")).currency == "EUR"

    def test_placeholder_dash_becomes_none(self):
        result = _parser.parse_details(_bond_page(emittent="--", zinssatz="--"))
        assert result.issuer is None
        assert result.coupon_rate_percent is None

    def test_missing_section_returns_empty_bond_details(self):
        result = _parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, BondDetails)
        assert result.issuer is None
        assert result.maturity_date is None

    def test_two_digit_year_date(self):
        assert _parser.parse_details(_bond_page(faelligkeit="15.01.30")).maturity_date == date(2030, 1, 15)

    def test_invalid_date_becomes_none(self):
        assert _parser.parse_details(_bond_page(faelligkeit="Open End")).maturity_date is None
