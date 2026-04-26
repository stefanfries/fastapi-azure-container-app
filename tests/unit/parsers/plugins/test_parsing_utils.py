"""
Unit tests for app.parsers.plugins.parsing_utils.

Covers:
- clean_float_value — German decimal string → float
- clean_numeric_value — German integer/magnitude string → int (incl. Bil.)
"""

import pytest

from app.parsers.plugins.parsing_utils import clean_float_value, clean_numeric_value


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


class TestCleanNumericValue:
    """clean_numeric_value — including Bil. (German trillion = 10^12)."""

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
