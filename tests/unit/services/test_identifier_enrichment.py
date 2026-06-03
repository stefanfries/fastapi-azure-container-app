"""Unit tests for _derive_yfinance_symbol in app.services.identifier_enrichment."""

from app.services.identifier_enrichment import _derive_yfinance_symbol


def _rec(ticker: str, exch_code: str) -> dict:
    return {"ticker": ticker, "exchCode": exch_code}


class TestDeriveYfinanceSymbol:
    def test_german_stock_prefers_xetra_over_us_otc(self) -> None:
        """German DAX stock: Xetra (GY) must win over US OTC (UP)."""
        records = [_rec("IFNNF", "UP"), _rec("IFX", "GY")]
        assert _derive_yfinance_symbol(records, "DE") == "IFX.DE"

    def test_us_stock_returns_no_suffix(self) -> None:
        """US stock: home exchange is US → no suffix."""
        records = [_rec("NVDA", "UN")]
        assert _derive_yfinance_symbol(records, "US") == "NVDA"

    def test_no_isin_country_falls_back_to_us_exchange(self) -> None:
        """No ISIN → no home-exchange match → Priority 2 picks US listing."""
        records = [_rec("AAPL", "UQ")]
        assert _derive_yfinance_symbol(records, None) == "AAPL"

    def test_german_stock_with_only_us_otc_falls_back_to_us(self) -> None:
        """German stock but no Xetra record → Priority 2 returns US OTC ticker."""
        records = [_rec("SIEGY", "UP")]
        assert _derive_yfinance_symbol(records, "DE") == "SIEGY"

    def test_unknown_country_with_non_us_exchange_falls_back_to_priority3(self) -> None:
        """Unknown country code + only a London record → Priority 3 returns it."""
        records = [_rec("TSCO", "LN")]
        assert _derive_yfinance_symbol(records, "XX") == "TSCO.L"

    def test_empty_records_returns_none(self) -> None:
        assert _derive_yfinance_symbol([], "DE") is None

    def test_slash_in_ticker_replaced_with_hyphen(self) -> None:
        """OpenFIGI uses '/' as share-class separator; Yahoo Finance uses '-'."""
        records = [_rec("BF/B", "UN")]
        assert _derive_yfinance_symbol(records, "US") == "BF-B"

    def test_records_with_unknown_exch_codes_ignored(self) -> None:
        """Records whose exchCode is not in _EXCH_TO_YAHOO_SUFFIX are skipped."""
        records = [_rec("IFNNF", "OQX"), _rec("IFX", "GY")]
        assert _derive_yfinance_symbol(records, "DE") == "IFX.DE"

    def test_records_with_only_unknown_exch_codes_returns_none(self) -> None:
        """All records filtered out → None."""
        records = [_rec("IFNNF", "OQX")]
        assert _derive_yfinance_symbol(records, "DE") is None
