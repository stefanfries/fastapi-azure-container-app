"""
Unit tests for app.parsers.plugins.factory.ParserFactory.

Covers:
- Each registered parser returns a non-None details object
"""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.parsers.plugins.bond_parser import BondParser
from app.parsers.plugins.certificate_parser import CertificateParser
from app.parsers.plugins.etf_parser import ETFParser
from app.parsers.plugins.fonds_parser import FondsParser
from app.parsers.plugins.stock_parser import StockParser


def _stock_page() -> BeautifulSoup:
    """Minimal stock page — used as a generic non-empty soup for dispatch tests."""
    html = """
    <html><body>
      <div class="col__content col__content--no-padding">
        <p class="headline headline--h3">Aktieninformationen</p>
        <div class="table__container--scroll">
          <table class="simple-table">
            <tr><th scope="row">Wertpapiertyp</th><td>Stammaktie</td></tr>
          </table>
        </div>
      </div>
    </body></html>
    """
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


class TestParseDetailsDispatch:
    @pytest.mark.parametrize("parser", [
        StockParser(),
        BondParser(),
        ETFParser(),
        FondsParser(),
        CertificateParser(),
    ])
    def test_returns_detail_object_not_none(self, parser):
        """All standard parsers return a details object (not None)."""
        assert parser.parse_details(_stock_page()) is not None
