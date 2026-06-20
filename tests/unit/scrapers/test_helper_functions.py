"""Unit tests for app.scrapers.helper_functions."""

from app.scrapers.helper_functions import convert_to_int


class TestConvertToInt:
    def test_plain_integer_string(self) -> None:
        assert convert_to_int("12345") == 12345

    def test_integer_with_period_thousands_separator(self) -> None:
        assert convert_to_int("1.234") == 1234

    def test_integer_with_comma_thousands_separator(self) -> None:
        assert convert_to_int("1,234") == 1234

    def test_mio_suffix_whole_number(self) -> None:
        assert convert_to_int("5 Mio") == 5_000_000

    def test_mio_suffix_decimal_comma(self) -> None:
        assert convert_to_int("1,5 Mio") == 1_500_000

    def test_mio_without_trailing_dot(self) -> None:
        # NOTE: "Mio." with a trailing dot is NOT supported — the dot survives
        # the replace("Mio", "") call and causes float() to raise ValueError.
        # Only the "Mio" variant (no trailing dot) is safe to pass.
        assert convert_to_int("3 Mio") == 3_000_000

    def test_leading_trailing_whitespace(self) -> None:
        assert convert_to_int("  42  ") == 42

    def test_mio_with_leading_whitespace(self) -> None:
        assert convert_to_int("  10 Mio  ") == 10_000_000
