"""Unit tests for app.services.identifier_enrichment."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.instruments import AssetClass
from app.services.identifier_enrichment import (
    _derive_cusip,
    _derive_yfinance_symbol,
    _pick_composite_figi,
    _pick_name,
    _rank_yfinance_candidates,
    build_global_identifiers,
)


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

    def test_rank_candidates_is_deterministic(self) -> None:
        records = [_rec("Q23", "SW"), _rec("BG", "UN"), _rec("BG", "US")]
        ranked = _rank_yfinance_candidates(records, "US")
        assert ranked[0][0] == "BG"
        assert ranked[0][1] == "home_exchange"


class TestDeriveCusip:
    def test_us_isin_extracts_cusip(self) -> None:
        assert _derive_cusip("US0378331005") == "037833100"

    def test_non_us_isin_returns_none(self) -> None:
        assert _derive_cusip("DE0007164600") is None

    def test_none_returns_none(self) -> None:
        assert _derive_cusip(None) is None

    def test_short_string_returns_none(self) -> None:
        assert _derive_cusip("US123") is None


class TestPickCompositeFigi:
    def test_prefers_us_exchange_record(self) -> None:
        records = [
            {"exchCode": "GY", "compositeFIGI": "BBG000GY"},
            {"exchCode": "UN", "compositeFIGI": "BBG000US"},
        ]
        assert _pick_composite_figi(records) == "BBG000US"

    def test_falls_back_to_first_with_figi(self) -> None:
        records = [
            {"exchCode": "GY", "compositeFIGI": "BBG000GY"},
            {"exchCode": "GF", "compositeFIGI": None},
        ]
        assert _pick_composite_figi(records) == "BBG000GY"

    def test_empty_records_returns_none(self) -> None:
        assert _pick_composite_figi([]) is None

    def test_all_null_figis_returns_none(self) -> None:
        records = [{"exchCode": "GY", "compositeFIGI": None}]
        assert _pick_composite_figi(records) is None


class TestPickName:
    def test_returns_first_non_null_name(self) -> None:
        records = [{"name": None}, {"name": "NVIDIA CORP"}, {"name": "NVIDIA"}]
        assert _pick_name(records) == "NVIDIA CORP"

    def test_empty_records_returns_none(self) -> None:
        assert _pick_name([]) is None

    def test_all_null_names_returns_none(self) -> None:
        assert _pick_name([{"name": None}]) is None


class TestBuildGlobalIdentifiers:
    async def test_skips_enrichment_for_warrant(self) -> None:
        result = await build_global_identifiers(
            isin="DE0007164600", wkn="716460", symbol_comdirect="SIE", asset_class=AssetClass.WARRANT
        )
        assert result.figi is None
        assert result.symbol_yfinance is None
        assert result.isin == "DE0007164600"

    async def test_skips_enrichment_for_certificate(self) -> None:
        result = await build_global_identifiers(
            isin=None, wkn="716460", symbol_comdirect="YYY", asset_class=AssetClass.CERTIFICATE
        )
        assert result.figi is None
        assert result.wkn == "716460"

    async def test_enriches_stock_via_isin(self) -> None:
        mock_records = [{"exchCode": "UN", "compositeFIGI": "BBG000NVD", "ticker": "NVDA", "name": "NVIDIA CORP"}]
        with patch(
            "app.services.identifier_enrichment.openfigi_client.map_by_isin",
            new=AsyncMock(return_value=mock_records),
        ), patch(
            "app.services.identifier_enrichment._has_recent_yahoo_prices",
            new=AsyncMock(return_value=True),
        ):
            result = await build_global_identifiers(
                isin="US67066G1040", wkn=None, symbol_comdirect="NVDA", asset_class=AssetClass.STOCK
            )
        assert result.figi == "BBG000NVD"
        assert result.symbol_yfinance == "NVDA"
        assert result.name_openfigi == "NVIDIA CORP"
        assert result.cusip == "67066G104"

    async def test_enriches_stock_via_wkn_when_no_isin(self) -> None:
        mock_records = [{"exchCode": "GY", "compositeFIGI": "BBG000GYX", "ticker": "SIE", "name": "SIEMENS AG"}]
        with patch(
            "app.services.identifier_enrichment.openfigi_client.map_by_wkn",
            new=AsyncMock(return_value=mock_records),
        ), patch(
            "app.services.identifier_enrichment._has_recent_yahoo_prices",
            new=AsyncMock(return_value=True),
        ):
            result = await build_global_identifiers(
                isin=None, wkn="723610", symbol_comdirect="SIE", asset_class=AssetClass.STOCK
            )
        assert result.figi == "BBG000GYX"
        assert result.symbol_yfinance == "SIE.DE"

    async def test_no_isin_no_wkn_returns_empty_identifiers(self) -> None:
        result = await build_global_identifiers(
            isin=None, wkn=None, symbol_comdirect="SYM", asset_class=AssetClass.STOCK
        )
        assert result.figi is None
        assert result.symbol_yfinance is None

    async def test_openfigi_failure_returns_gracefully(self) -> None:
        with patch(
            "app.services.identifier_enrichment.openfigi_client.map_by_isin",
            new=AsyncMock(side_effect=Exception("network error")),
        ):
            result = await build_global_identifiers(
                isin="US0378331005", wkn=None, symbol_comdirect="AAPL", asset_class=AssetClass.STOCK
            )
        assert result.figi is None
        assert result.symbol_yfinance is None

    async def test_known_overrides_return_expected_symbols(self) -> None:
        with patch(
            "app.services.identifier_enrichment.openfigi_client.map_by_isin",
            new=AsyncMock(return_value=[]),
        ):
            bg = await build_global_identifiers(
                isin="CH1300646267",
                wkn=None,
                symbol_comdirect="Q23",
                asset_class=AssetClass.STOCK,
            )
            cb = await build_global_identifiers(
                isin="CH0044328745",
                wkn=None,
                symbol_comdirect="CB",
                asset_class=AssetClass.STOCK,
            )
            grmn = await build_global_identifiers(
                isin="CH0114405324",
                wkn=None,
                symbol_comdirect="GRMN",
                asset_class=AssetClass.STOCK,
            )

        assert bg.symbol_yfinance == "BG"
        assert cb.symbol_yfinance == "CB"
        assert grmn.symbol_yfinance == "GRMN"

    async def test_validation_promotes_next_viable_candidate(self) -> None:
        records = [
            {"exchCode": "GY", "compositeFIGI": "BBG001", "ticker": "ABC", "name": "ABC AG"},
            {"exchCode": "UN", "compositeFIGI": "BBG002", "ticker": "ABCU", "name": "ABC AG"},
        ]
        with patch(
            "app.services.identifier_enrichment.openfigi_client.map_by_isin",
            new=AsyncMock(return_value=records),
        ), patch(
            "app.services.identifier_enrichment._has_recent_yahoo_prices",
            new=AsyncMock(side_effect=[False, True]),
        ):
            result = await build_global_identifiers(
                isin="DE0007164600", wkn=None, symbol_comdirect="ABC", asset_class=AssetClass.STOCK
            )
        assert result.symbol_yfinance == "ABCU"
