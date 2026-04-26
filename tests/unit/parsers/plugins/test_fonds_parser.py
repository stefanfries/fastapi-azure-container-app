"""Unit tests for app.parsers.plugins.fonds_parser.FondsParser."""

import textwrap
from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import FondsDetails
from app.parsers.plugins.fonds_parser import FondsParser


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
    return _section_page("Stammdaten", [
        ("Fondskategorie", fund_type),
        ("Fondsmanager", fund_manager),
        ("Auflagedatum", inception),
        ("Fondsdomizil", domicile),
        ("Art", distribution),
        ("Laufende Kosten", ter),
        ("W\u00e4hrung", currency),
        ("Fondsvolumen", fund_size),
    ])


_parser = FondsParser()


class TestFondsDetailsParser:
    def test_returns_fonds_details_instance(self):
        assert isinstance(_parser.parse_details(_fonds_page()), FondsDetails)

    def test_discriminator(self):
        assert _parser.parse_details(_fonds_page()).asset_class == "Fund"

    def test_fund_type(self):
        assert _parser.parse_details(_fonds_page(fund_type="Aktienfonds")).fund_type == "Aktienfonds"

    def test_fund_manager(self):
        assert _parser.parse_details(_fonds_page(fund_manager="BlackRock")).fund_manager == "BlackRock"

    def test_inception_date(self):
        assert _parser.parse_details(_fonds_page(inception="01.04.1994")).inception_date == date(1994, 4, 1)

    def test_distribution_policy(self):
        assert _parser.parse_details(_fonds_page(distribution="ausschüttend")).distribution_policy == "ausschüttend"

    def test_distribution_policy_normalizes_whitespace(self):
        raw = "Ausschüttend\n                        (zuletzt 16.06.25 0,78 EUR)"
        assert _parser.parse_details(_fonds_page(distribution=raw)).distribution_policy == "Ausschüttend (zuletzt 16.06.25 0,78 EUR)"

    def test_expense_ratio_percent(self):
        assert _parser.parse_details(_fonds_page(ter="1,50 %")).expense_ratio_percent == pytest.approx(1.50)

    def test_fund_currency(self):
        assert _parser.parse_details(_fonds_page(currency="EUR")).fund_currency == "EUR"

    def test_fund_size_mio(self):
        assert _parser.parse_details(_fonds_page(fund_size="512,00 Mio.")).fund_size == pytest.approx(512_000_000.0)

    def test_fund_size_mrd(self):
        assert _parser.parse_details(_fonds_page(fund_size="3,10 Mrd.")).fund_size == pytest.approx(3_100_000_000.0)

    def test_placeholder_becomes_none(self):
        result = _parser.parse_details(_fonds_page(fund_type="--", fund_manager="--"))
        assert result.fund_type is None
        assert result.fund_manager is None

    def test_missing_section_returns_empty_fonds_details(self):
        result = _parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, FondsDetails)
        assert result.fund_type is None
