"""Unit tests for app.parsers.warrant_detail — helpers and reference-data parsing."""

from datetime import date

import pytest
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _soup_from_rows(rows: list[tuple[str, str]], heading: str = "Stammdaten") -> BeautifulSoup:
    """Wrap (label, value) pairs in a section that matches _section_table()."""
    row_html = "\n".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    html = f"""
    <div>
        <h2>{heading}</h2>
        <table>{row_html}</table>
    </div>
    """
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# _parse_float
# ---------------------------------------------------------------------------


class TestParseFloat:
    def test_german_decimal(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("0,75 %") == pytest.approx(0.75)

    def test_thousands_separator(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("1.234,56 EUR") == pytest.approx(1234.56)

    def test_integer_value(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("220") == pytest.approx(220.0)

    def test_double_dash_returns_none(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("--") is None

    def test_empty_returns_none(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("") is None

    def test_none_returns_none(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float(None) is None

    def test_k_a_returns_none(self):
        from app.parsers.warrant_detail import _parse_float

        assert _parse_float("k. A.") is None


# ---------------------------------------------------------------------------
# _parse_amount_currency
# ---------------------------------------------------------------------------


class TestParseAmountCurrency:
    def test_value_and_currency(self):
        from app.parsers.warrant_detail import _parse_amount_currency

        value, currency = _parse_amount_currency("240,00 USD")
        assert value == pytest.approx(240.0)
        assert currency == "USD"

    def test_eur_currency(self):
        from app.parsers.warrant_detail import _parse_amount_currency

        value, currency = _parse_amount_currency("1.234,56 EUR")
        assert value == pytest.approx(1234.56)
        assert currency == "EUR"

    def test_double_dash_returns_none_pair(self):
        from app.parsers.warrant_detail import _parse_amount_currency

        assert _parse_amount_currency("--") == (None, None)

    def test_none_returns_none_pair(self):
        from app.parsers.warrant_detail import _parse_amount_currency

        assert _parse_amount_currency(None) == (None, None)

    def test_value_without_currency(self):
        from app.parsers.warrant_detail import _parse_amount_currency

        value, currency = _parse_amount_currency("220,00")
        assert value == pytest.approx(220.0)
        assert currency is None


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_two_digit_year(self):
        from app.parsers.warrant_detail import _parse_date

        assert _parse_date("16.06.27") == date(2027, 6, 16)

    def test_four_digit_year(self):
        from app.parsers.warrant_detail import _parse_date

        assert _parse_date("16.06.2027") == date(2027, 6, 16)

    def test_double_dash_returns_none(self):
        from app.parsers.warrant_detail import _parse_date

        assert _parse_date("--") is None

    def test_none_returns_none(self):
        from app.parsers.warrant_detail import _parse_date

        assert _parse_date(None) is None


# ---------------------------------------------------------------------------
# _parse_reference_data — capped warrant
# ---------------------------------------------------------------------------


class TestParseReferenceDataCapped:
    """UN2U70-style: Stammdaten contains a 'Cap' row."""

    _ROWS = [
        ("letzter Handelstag", "16.06.27"),
        ("Fälligkeit", "16.06.27"),
        ("Basispreis", "220,00 USD"),
        ("Cap", "240,00 USD"),
        ("Basiswert", "NVIDIA Corp."),
        ("Kurs Basiswert", "216,09 USD"),
        ("Bezugsverhältnis", "1 : 1"),
        ("Typ", "Call ( Euro. )"),
        ("Emittent", "UniCredit"),
        ("Währung", "EUR"),
        ("Symbol", "--"),
        ("ISIN", "DE000UN2U707"),
        ("WKN", "UN2U70"),
    ]

    def _parse(self):
        from app.parsers.warrant_detail import _parse_reference_data

        soup = _soup_from_rows(self._ROWS)
        return _parse_reference_data(soup)

    def test_is_capped_true(self):
        assert self._parse().is_capped is True

    def test_cap_value(self):
        assert self._parse().cap == pytest.approx(240.0)

    def test_cap_currency(self):
        assert self._parse().cap_currency == "USD"

    def test_strike_still_parsed(self):
        rd = self._parse()
        assert rd.strike == pytest.approx(220.0)
        assert rd.strike_currency == "USD"

    def test_maturity_date(self):
        assert self._parse().maturity_date == date(2027, 6, 16)

    def test_wkn(self):
        assert self._parse().wkn == "UN2U70"

    def test_isin(self):
        assert self._parse().isin == "DE000UN2U707"


# ---------------------------------------------------------------------------
# _parse_reference_data — regular (uncapped) warrant
# ---------------------------------------------------------------------------


class TestParseReferenceDataUncapped:
    """MK9L2L-style: Stammdaten has no 'Cap' row."""

    _ROWS = [
        ("letzter Handelstag", "17.06.27"),
        ("Fälligkeit", "17.06.27"),
        ("Basispreis", "220,00 USD"),
        ("Basiswert", "NVIDIA Corp."),
        ("Kurs Basiswert", "216,09 USD"),
        ("Bezugsverhältnis", "10 : 1"),
        ("Typ", "Call ( Amer. )"),
        ("Emittent", "Morgan Stanley"),
        ("Währung", "EUR"),
        ("Symbol", "--"),
        ("ISIN", "DE000MK9L2L9"),
        ("WKN", "MK9L2L"),
    ]

    def _parse(self):
        from app.parsers.warrant_detail import _parse_reference_data

        soup = _soup_from_rows(self._ROWS)
        return _parse_reference_data(soup)

    def test_is_capped_false(self):
        assert self._parse().is_capped is False

    def test_cap_none(self):
        assert self._parse().cap is None

    def test_cap_currency_none(self):
        assert self._parse().cap_currency is None

    def test_strike_parsed(self):
        rd = self._parse()
        assert rd.strike == pytest.approx(220.0)
        assert rd.strike_currency == "USD"

    def test_ratio(self):
        assert self._parse().ratio == "10 : 1"
