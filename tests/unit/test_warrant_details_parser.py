"""
Unit tests for warrant-details parsing.

Covers:
- ``WarrantParser.parse_details``
    - Full warrant Stammdaten: all fields extracted correctly
    - warrant_type reconstructed from span title: "Call (Amerikanisch)"
    - underlying_name from <span title> (not truncated display text)
    - underlying_link built from <a href> (absolute comdirect URL)
    - issuer full name from <a title> attribute
    - Strike split into value + currency
    - Maturity / last-trading-day date parsing (DD.MM.YY and DD.MM.YYYY)
    - Missing / "--" / "k. A." fields become None
    - No Stammdaten section returns WarrantDetails with all None fields
    - Fallbacks when span/a attributes are absent
"""

import textwrap
from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.models.instrument_details import WarrantDetails
from app.parsers.plugins.warrant_parser import WarrantParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _warrant_page(
    *,
    typ: str = 'Call (<span title="Amerikanisch">Amer.</span>)',
    basiswert: str = '<a href="/inf/aktien/US67066G1040" title="NVIDIA Corporation"><span title="NVIDIA Corporation">NVIDIA Corp ..</span></a>',
    basispreis: str = "100,00 USD",
    bezugsverhaeltnis: str = "10 : 1",
    faelligkeit: str = "18.06.26",
    letzter_handelstag: str = "17.06.26",
    emittent: str = '<a href="/inf/optionsscheine/emittenten/hsbc.html" title="HSBC, Deutschland, Düsseldorf">HSBC</a>',
) -> BeautifulSoup:
    """Return a minimal BeautifulSoup page matching the real comdirect warrant Stammdaten HTML."""
    html = f"""
    <html><body>
      <div>
        <h2>Stammdaten</h2>
        <table class="simple-table">
          <tbody>
            <tr><th>letzter Handelstag</th><td>{letzter_handelstag}</td></tr>
            <tr><th>Fälligkeit</th><td>{faelligkeit}</td></tr>
            <tr><th>Basispreis</th><td>{basispreis}</td></tr>
            <tr><th>Basiswert</th><td>{basiswert}</td></tr>
            <tr><th>Bezugsverhältnis</th><td>{bezugsverhaeltnis}</td></tr>
            <tr><th>Typ</th><td>{typ}</td></tr>
            <tr><th>Emittent</th><td>{emittent}</td></tr>
          </tbody>
        </table>
      </div>
    </body></html>
    """
    return _make_soup(html)


_parser = WarrantParser()

# ---------------------------------------------------------------------------
# warrant_type — span title expansion
# ---------------------------------------------------------------------------


class TestWarrantType:
    def test_call_amerikanisch(self):
        soup = _warrant_page(typ='Call (<span title="Amerikanisch">Amer.</span>)')
        assert _parser.parse_details(soup).warrant_type == "Call (Amerikanisch)"

    def test_put_europaeisch(self):
        soup = _warrant_page(typ='Put (<span title="Europäisch">Europ.</span>)')
        assert _parser.parse_details(soup).warrant_type == "Put (Europäisch)"

    def test_plain_text_fallback(self):
        """No span — plain text is returned as-is."""
        soup = _warrant_page(typ="Call (Amer.)")
        assert _parser.parse_details(soup).warrant_type == "Call (Amer.)"

    def test_dash_returns_none(self):
        soup = _warrant_page(typ="--")
        assert _parser.parse_details(soup).warrant_type is None


# ---------------------------------------------------------------------------
# underlying_name — from span title
# ---------------------------------------------------------------------------


class TestUnderlyingName:
    def test_full_name_from_span_title(self):
        soup = _warrant_page(
            basiswert='<a href="/inf/aktien/US67066G1040" title="NVIDIA Corporation">'
                      '<span title="NVIDIA Corporation">NVIDIA Corp ..</span></a>'
        )
        assert _parser.parse_details(soup).underlying_name == "NVIDIA Corporation"

    def test_falls_back_to_a_title_when_no_span(self):
        soup = _warrant_page(
            basiswert='<a href="/inf/aktien/US67066G1040" title="NVIDIA Corporation">NVIDIA Corp ..</a>'
        )
        assert _parser.parse_details(soup).underlying_name == "NVIDIA Corporation"

    def test_falls_back_to_text_when_no_a(self):
        soup = _warrant_page(basiswert="NVIDIA Corp.")
        assert _parser.parse_details(soup).underlying_name == "NVIDIA Corp."

    def test_dash_returns_none(self):
        soup = _warrant_page(basiswert="--")
        assert _parser.parse_details(soup).underlying_name is None

    def test_ka_returns_none(self):
        soup = _warrant_page(
            basiswert='<a href="/x" title="k. A."><span title="k. A.">k. A.</span></a>'
        )
        assert _parser.parse_details(soup).underlying_name is None


# ---------------------------------------------------------------------------
# underlying_link — from <a href>
# ---------------------------------------------------------------------------


class TestUnderlyingLink:
    def test_absolute_url_built_from_relative_href(self):
        soup = _warrant_page(
            basiswert='<a href="/inf/aktien/US67066G1040" title="NVIDIA"><span title="NVIDIA">NV..</span></a>'
        )
        result = _parser.parse_details(soup)
        assert result.underlying_link == "https://www.comdirect.de/inf/aktien/US67066G1040"

    def test_absolute_href_kept_as_is(self):
        soup = _warrant_page(
            basiswert='<a href="https://example.com/asset" title="Asset">Asset</a>'
        )
        assert _parser.parse_details(soup).underlying_link == "https://example.com/asset"

    def test_no_link_when_no_anchor(self):
        soup = _warrant_page(basiswert="NVIDIA Corp.")
        assert _parser.parse_details(soup).underlying_link is None


# ---------------------------------------------------------------------------
# issuer — from <a title>
# ---------------------------------------------------------------------------


class TestIssuer:
    def test_full_name_from_a_title(self):
        soup = _warrant_page(
            emittent='<a href="/inf/optionsscheine/emittenten/hsbc.html" title="HSBC, Deutschland, Düsseldorf">HSBC</a>'
        )
        assert _parser.parse_details(soup).issuer == "HSBC, Deutschland, Düsseldorf"

    def test_falls_back_to_anchor_text_when_no_title(self):
        soup = _warrant_page(
            emittent='<a href="/inf/optionsscheine/emittenten/gsb.html">Goldman Sachs</a>'
        )
        assert _parser.parse_details(soup).issuer == "Goldman Sachs"

    def test_falls_back_to_plain_text_when_no_anchor(self):
        soup = _warrant_page(emittent="Goldman Sachs")
        assert _parser.parse_details(soup).issuer == "Goldman Sachs"

    def test_dash_returns_none(self):
        soup = _warrant_page(emittent="--")
        assert _parser.parse_details(soup).issuer is None

    def test_ka_a_title_returns_none(self):
        soup = _warrant_page(emittent='<a href="/x" title="k. A.">k. A.</a>')
        assert _parser.parse_details(soup).issuer is None


# ---------------------------------------------------------------------------
# strike
# ---------------------------------------------------------------------------


class TestStrike:
    def test_value_and_currency(self):
        soup = _warrant_page(basispreis="100,00 USD")
        result = _parser.parse_details(soup)
        assert result.strike == pytest.approx(100.0)
        assert result.strike_currency == "USD"

    def test_eur(self):
        soup = _warrant_page(basispreis="225,50 EUR")
        result = _parser.parse_details(soup)
        assert result.strike == pytest.approx(225.5)
        assert result.strike_currency == "EUR"

    def test_thousands_separator(self):
        soup = _warrant_page(basispreis="1.234,56 USD")
        result = _parser.parse_details(soup)
        assert result.strike == pytest.approx(1234.56)

    def test_dash_returns_none(self):
        soup = _warrant_page(basispreis="--")
        result = _parser.parse_details(soup)
        assert result.strike is None
        assert result.strike_currency is None


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------


class TestDates:
    def test_maturity_short_year(self):
        assert _parser.parse_details(_warrant_page(faelligkeit="18.06.26")).maturity_date == date(2026, 6, 18)

    def test_maturity_full_year(self):
        assert _parser.parse_details(_warrant_page(faelligkeit="18.06.2026")).maturity_date == date(2026, 6, 18)

    def test_last_trading_day_short_year(self):
        assert _parser.parse_details(_warrant_page(letzter_handelstag="17.06.26")).last_trading_day == date(2026, 6, 17)

    def test_last_trading_day_full_year(self):
        assert _parser.parse_details(_warrant_page(letzter_handelstag="17.06.2026")).last_trading_day == date(2026, 6, 17)

    def test_dash_maturity_returns_none(self):
        assert _parser.parse_details(_warrant_page(faelligkeit="--")).maturity_date is None

    def test_dash_last_trading_day_returns_none(self):
        assert _parser.parse_details(_warrant_page(letzter_handelstag="--")).last_trading_day is None


# ---------------------------------------------------------------------------
# other fields + no section
# ---------------------------------------------------------------------------


class TestMiscFields:
    def test_ratio(self):
        assert _parser.parse_details(_warrant_page(bezugsverhaeltnis="10 : 1")).ratio == "10 : 1"

    def test_dash_ratio_returns_none(self):
        assert _parser.parse_details(_warrant_page(bezugsverhaeltnis="--")).ratio is None

    def test_asset_class_literal(self):
        assert _parser.parse_details(_warrant_page()).asset_class == "Warrant"

    def test_no_stammdaten_section_all_none(self):
        soup = _make_soup("<html><body><p>No table here</p></body></html>")
        result = _parser.parse_details(soup)
        assert isinstance(result, WarrantDetails)
        assert result.warrant_type is None
        assert result.underlying_name is None
        assert result.underlying_link is None
        assert result.strike is None
        assert result.issuer is None

