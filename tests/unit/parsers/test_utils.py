"""
Unit tests for app.parsers.utils — pure utility functions.

Covers:
- check_valid_id_notation: valid (passes) / invalid (raises HTTP 400)
- get_id_notations_dict: merges lt + ex venue dicts
- get_trading_venues_dict: produces id_notation → venue reverse map
- get_id_notation: looks up id_notation by venue name; raises ValueError when missing
- get_trading_venue: looks up venue name by id_notation; raises ValueError when missing
- round_time: partial time string → full HH:MM:SS.ffffff (all match cases, up=True/False)
- round_datetime: partial ISO-8601 date/datetime → full string (all match cases, up=True/False)
"""

import pytest
from fastapi import HTTPException

from app.models.instruments import AssetClass, Instrument, VenueInfo
from app.parsers.utils import (
    check_valid_id_notation,
    get_id_notation,
    get_id_notations_dict,
    get_trading_venue,
    get_trading_venues_dict,
    round_datetime,
    round_time,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _instrument(lt: dict[str, str] | None = None, ex: dict[str, str] | None = None) -> Instrument:
    return Instrument(
        name="Test",
        wkn="918422",
        asset_class=AssetClass.STOCK,
        id_notations_life_trading={
            k: VenueInfo(id_notation=v) for k, v in (lt or {}).items()
        },
        id_notations_exchange_trading={
            k: VenueInfo(id_notation=v) for k, v in (ex or {}).items()
        },
    )


# ---------------------------------------------------------------------------
# check_valid_id_notation
# ---------------------------------------------------------------------------

class TestCheckValidIdNotation:
    def test_valid_in_lt_passes(self):
        instrument = _instrument(lt={"LT HSBC": "111"})
        result = check_valid_id_notation(instrument, "111")
        assert result is None

    def test_valid_in_ex_passes(self):
        instrument = _instrument(ex={"Xetra": "222"})
        result = check_valid_id_notation(instrument, "222")
        assert result is None

    def test_invalid_raises_400(self):
        instrument = _instrument(lt={"LT HSBC": "111"})
        with pytest.raises(HTTPException) as exc_info:
            check_valid_id_notation(instrument, "999")
        assert exc_info.value.status_code == 400

    def test_empty_venues_raises_400(self):
        instrument = _instrument()
        with pytest.raises(HTTPException) as exc_info:
            check_valid_id_notation(instrument, "111")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# get_id_notations_dict
# ---------------------------------------------------------------------------

class TestGetIdNotationsDict:
    def test_merges_lt_and_ex(self):
        instrument = _instrument(lt={"LT HSBC": "111"}, ex={"Xetra": "222"})
        merged = get_id_notations_dict(instrument)
        assert "LT HSBC" in merged
        assert "Xetra" in merged
        assert merged["LT HSBC"].id_notation == "111"
        assert merged["Xetra"].id_notation == "222"

    def test_empty_when_no_venues(self):
        instrument = _instrument()
        assert get_id_notations_dict(instrument) == {}

    def test_lt_only(self):
        instrument = _instrument(lt={"LT HSBC": "111"})
        result = get_id_notations_dict(instrument)
        assert len(result) == 1
        assert "LT HSBC" in result


# ---------------------------------------------------------------------------
# get_trading_venues_dict
# ---------------------------------------------------------------------------

class TestGetTradingVenuesDict:
    def test_reverse_mapping(self):
        instrument = _instrument(lt={"LT HSBC": "111"}, ex={"Xetra": "222"})
        rev = get_trading_venues_dict(instrument)
        assert rev["111"] == "LT HSBC"
        assert rev["222"] == "Xetra"

    def test_empty_result_for_no_venues(self):
        instrument = _instrument()
        assert get_trading_venues_dict(instrument) == {}


# ---------------------------------------------------------------------------
# get_id_notation
# ---------------------------------------------------------------------------

class TestGetIdNotation:
    def test_found_in_lt(self):
        instrument = _instrument(lt={"LT HSBC": "111"})
        assert get_id_notation(instrument, "LT HSBC") == "111"

    def test_found_in_ex(self):
        instrument = _instrument(ex={"Xetra": "222"})
        assert get_id_notation(instrument, "Xetra") == "222"

    def test_not_found_raises_value_error(self):
        instrument = _instrument(lt={"LT HSBC": "111"})
        with pytest.raises(ValueError, match="Invalid trading_venue"):
            get_id_notation(instrument, "Unknown")


# ---------------------------------------------------------------------------
# get_trading_venue
# ---------------------------------------------------------------------------

class TestGetTradingVenue:
    def test_found(self):
        instrument = _instrument(ex={"Xetra": "222"})
        assert get_trading_venue(instrument, "222") == "Xetra"

    def test_not_found_raises_value_error(self):
        instrument = _instrument(ex={"Xetra": "222"})
        with pytest.raises(ValueError, match="Invalid id_notation"):
            get_trading_venue(instrument, "999")


# ---------------------------------------------------------------------------
# round_time
# ---------------------------------------------------------------------------

class TestRoundTime:
    # --- case 3: HH:MM:SS ---
    def test_full_time_down(self):
        assert round_time("14:30:00") == "14:30:00.000000"

    def test_full_time_up(self):
        assert round_time("14:30:00", up=True) == "14:30:00.999999"

    def test_full_time_with_microseconds_preserved(self):
        assert round_time("14:30:00.123456") == "14:30:00.123456"

    # --- case 2: HH:MM ---
    def test_hhmm_down(self):
        # down: no seconds appended — returns as-is
        assert round_time("14:30") == "14:30"

    def test_hhmm_up(self):
        assert round_time("14:30", up=True) == "14:30:59.999999"

    # --- case 1: HH ---
    def test_hour_only_down(self):
        assert round_time("14") == "14"

    def test_hour_only_up(self):
        assert round_time("14", up=True) == "14:59:59.999999"


# ---------------------------------------------------------------------------
# round_datetime
# ---------------------------------------------------------------------------

class TestRoundDatetime:
    # --- case 3: YYYY-MM-DD ---
    def test_full_date_down(self):
        result = round_datetime("2024-03-15")
        assert result.startswith("2024-03-15T")

    def test_full_date_up(self):
        result = round_datetime("2024-03-15", up=True)
        assert result.startswith("2024-03-15T")

    # --- case 2: YYYY-MM ---
    def test_year_month_down(self):
        result = round_datetime("2024-03")
        assert result.startswith("2024-03-01T")

    def test_year_month_up(self):
        result = round_datetime("2024-03", up=True)
        assert result.startswith("2024-03-31T")

    def test_year_month_up_february_non_leap(self):
        result = round_datetime("2023-02", up=True)
        assert result.startswith("2023-02-28T")

    def test_year_month_up_february_leap(self):
        result = round_datetime("2024-02", up=True)
        assert result.startswith("2024-02-29T")

    # --- case 1: YYYY ---
    def test_year_only_down(self):
        result = round_datetime("2024")
        assert result.startswith("2024-01-01T")

    def test_year_only_up(self):
        result = round_datetime("2024", up=True)
        assert result.startswith("2024-12-31T")

    # --- with T component ---
    def test_full_datetime_string(self):
        result = round_datetime("2024-03-15T14:30")
        assert result.startswith("2024-03-15T14:30")
