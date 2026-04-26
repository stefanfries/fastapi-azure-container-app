"""Unit tests for app.parsers.plugins.etf_parser.ETFParser."""

import textwrap
from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import ETFDetails
from app.parsers.plugins.etf_parser import ETFParser


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
    return _section_page("Stammdaten", [
        ("Vergleichsindex", index),
        ("Laufende Kosten", ter),
        ("Abbildungsart", replication),
        ("Art", distribution),
        ("Fondsdomizil", domicile),
        ("Auflagedatum", inception),
        ("W\u00e4hrung", currency),
        ("Fondsvolumen", fund_size),
    ])


_parser = ETFParser()


class TestETFDetailsParser:
    def test_returns_etf_details_instance(self):
        assert isinstance(_parser.parse_details(_etf_page()), ETFDetails)

    def test_discriminator(self):
        assert _parser.parse_details(_etf_page()).asset_class == "ETF"

    def test_tracked_index(self):
        assert _parser.parse_details(_etf_page(index="MSCI World")).tracked_index == "MSCI World"

    def test_expense_ratio_percent(self):
        assert _parser.parse_details(_etf_page(ter="0,20 %")).expense_ratio_percent == pytest.approx(0.20)

    def test_replication_method(self):
        assert _parser.parse_details(_etf_page(replication="physisch")).replication_method == "physisch"

    def test_distribution_policy(self):
        assert _parser.parse_details(_etf_page(distribution="thesaurierend")).distribution_policy == "thesaurierend"

    def test_inception_date(self):
        assert _parser.parse_details(_etf_page(inception="25.10.2005")).inception_date == date(2005, 10, 25)

    def test_fund_currency(self):
        assert _parser.parse_details(_etf_page(currency="USD")).fund_currency == "USD"

    def test_fund_size_mrd(self):
        assert _parser.parse_details(_etf_page(fund_size="1,23 Mrd.")).fund_size == pytest.approx(1_230_000_000.0)

    def test_fund_size_mio(self):
        assert _parser.parse_details(_etf_page(fund_size="512,00 Mio.")).fund_size == pytest.approx(512_000_000.0)

    def test_fund_size_placeholder(self):
        assert _parser.parse_details(_etf_page(fund_size="--")).fund_size is None

    def test_placeholder_becomes_none(self):
        result = _parser.parse_details(_etf_page(index="--", replication="--"))
        assert result.tracked_index is None
        assert result.replication_method is None

    def test_missing_section_returns_empty_etf_details(self):
        result = _parser.parse_details(_make_soup("<html><body><p>No data</p></body></html>"))
        assert isinstance(result, ETFDetails)
        assert result.tracked_index is None
