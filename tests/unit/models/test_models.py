"""
Unit tests for app.models.depots, app.models.history, and app.models.indices.

Focus: Pydantic field constraints (WKN/ISIN regex), required-field enforcement,
and correct round-trip via model_dump().  These are contract tests — they catch
accidental changes to the model interface.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.depots import Depot, DepotItem
from app.models.history import HistoryData, HistoryRecord
from app.models.indices import IndexInfo, IndexMember

# ===========================================================================
# Depot models
# ===========================================================================

class TestDepotItem:
    _VALID = dict(
        wkn="716460",
        name="SAP SE",
        amount=10,
        buy_price=185.50,
        buy_date=datetime(2024, 1, 15, 10, 30),
    )

    def test_valid_item_accepted(self):
        item = DepotItem(**self._VALID)
        assert item.wkn == "716460"
        assert item.amount == 10

    def test_invalid_wkn_too_short(self):
        with pytest.raises(ValidationError, match="wkn"):
            DepotItem(**{**self._VALID, "wkn": "123"})

    def test_invalid_wkn_too_long(self):
        with pytest.raises(ValidationError, match="wkn"):
            DepotItem(**{**self._VALID, "wkn": "1234567"})

    def test_invalid_wkn_contains_i(self):
        with pytest.raises(ValidationError, match="wkn"):
            DepotItem(**{**self._VALID, "wkn": "I12345"})

    def test_invalid_wkn_contains_o(self):
        with pytest.raises(ValidationError, match="wkn"):
            DepotItem(**{**self._VALID, "wkn": "O12345"})

    def test_missing_required_field_raises(self):
        data = {k: v for k, v in self._VALID.items() if k != "name"}
        with pytest.raises(ValidationError, match="name"):
            DepotItem(**data)


class TestDepot:
    _NOW = datetime(2024, 6, 1, 12, 0)
    _ITEM = dict(
        wkn="716460",
        name="SAP SE",
        amount=5,
        buy_price=190.0,
        buy_date=datetime(2024, 1, 1),
    )

    def _valid(self, **overrides):
        base = dict(
            id="depot-1",
            name="My Depot",
            items=[DepotItem(**self._ITEM)],
            cash=1000.0,
            created_at=self._NOW,
            changed_at=self._NOW,
        )
        return {**base, **overrides}

    def test_valid_depot_accepted(self):
        depot = Depot(**self._valid())
        assert depot.id == "depot-1"
        assert len(depot.items) == 1
        assert depot.cash == pytest.approx(1000.0)

    def test_empty_items_list_accepted(self):
        depot = Depot(**self._valid(items=[]))
        assert depot.items == []

    def test_missing_id_raises(self):
        data = {k: v for k, v in self._valid().items() if k != "id"}
        with pytest.raises(ValidationError, match="id"):
            Depot(**data)

    def test_model_dump_roundtrip(self):
        depot = Depot(**self._valid())
        dumped = depot.model_dump()
        assert dumped["name"] == "My Depot"
        assert dumped["cash"] == pytest.approx(1000.0)
        assert len(dumped["items"]) == 1


# ===========================================================================
# History models
# ===========================================================================

class TestHistoryRecord:
    _VALID = dict(
        datetime=datetime(2026, 1, 2, 9, 0),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.5,
        volume=1_000_000,
    )

    def test_valid_record_accepted(self):
        rec = HistoryRecord(**self._VALID)
        assert rec.close == pytest.approx(103.5)
        assert rec.volume == 1_000_000

    def test_missing_open_raises(self):
        data = {k: v for k, v in self._VALID.items() if k != "open"}
        with pytest.raises(ValidationError, match="open"):
            HistoryRecord(**data)


class TestHistoryData:
    _RECORD = dict(
        datetime=datetime(2026, 1, 2),
        open=100.0, high=105.0, low=99.0, close=103.5, volume=500_000,
    )
    _VALID = dict(
        name="SAP SE",
        wkn="716460",
        isin="DE0007164600",
        id_notation="12345",
        trading_venue="XETRA",
        currency="EUR",
        start=datetime(2026, 1, 1),
        end=datetime(2026, 1, 31),
        interval="day",
        data=[],
    )

    def test_valid_history_data_accepted(self):
        hd = HistoryData(**self._VALID)
        assert hd.interval == "day"
        assert hd.currency == "EUR"

    def test_isin_is_optional(self):
        data = {k: v for k, v in self._VALID.items() if k != "isin"}
        hd = HistoryData(**data)
        assert hd.isin is None

    def test_invalid_wkn_raises(self):
        with pytest.raises(ValidationError, match="wkn"):
            HistoryData(**{**self._VALID, "wkn": "TOOLONG"})

    def test_invalid_isin_raises(self):
        with pytest.raises(ValidationError, match="isin"):
            HistoryData(**{**self._VALID, "isin": "BADISIN"})

    def test_invalid_interval_raises(self):
        with pytest.raises(ValidationError, match="interval"):
            HistoryData(**{**self._VALID, "interval": "year"})

    def test_data_list_with_records(self):
        hd = HistoryData(**{**self._VALID, "data": [HistoryRecord(**self._RECORD)]})
        assert len(hd.data) == 1
        assert hd.data[0].close == pytest.approx(103.5)


# ===========================================================================
# Indices models
# ===========================================================================

class TestIndexInfo:
    _VALID = dict(
        name="DAX",
        wkn="846900",
        member_count=40,
        link="https://www.comdirect.de/inf/indizes/detail/uebersicht.html?SEARCH_VALUE=846900",
    )

    def test_valid_index_info_accepted(self):
        info = IndexInfo(**self._VALID)
        assert info.name == "DAX"
        assert info.member_count == 40

    def test_wkn_is_optional(self):
        data = {k: v for k, v in self._VALID.items() if k != "wkn"}
        info = IndexInfo(**data)
        assert info.wkn is None

    def test_invalid_wkn_raises(self):
        with pytest.raises(ValidationError, match="wkn"):
            IndexInfo(**{**self._VALID, "wkn": "TOOLONG"})

    def test_missing_member_count_raises(self):
        data = {k: v for k, v in self._VALID.items() if k != "member_count"}
        with pytest.raises(ValidationError, match="member_count"):
            IndexInfo(**data)


class TestIndexMember:
    _VALID = dict(
        name="SAP SE",
        isin="DE0007164600",
        link="https://www.comdirect.de/inf/aktien/detail/uebersicht.html?SEARCH_VALUE=DE0007164600",
        asset_class="Stock",
        instrument_url="/v1/instruments/DE0007164600",
    )

    def test_valid_member_accepted(self):
        member = IndexMember(**self._VALID)
        assert member.isin == "DE0007164600"
        assert member.instrument_url == "/v1/instruments/DE0007164600"

    def test_asset_class_is_optional(self):
        data = {k: v for k, v in self._VALID.items() if k != "asset_class"}
        member = IndexMember(**data)
        assert member.asset_class is None

    def test_invalid_isin_too_short(self):
        with pytest.raises(ValidationError, match="isin"):
            IndexMember(**{**self._VALID, "isin": "DE000716460"})

    def test_invalid_isin_lowercase(self):
        with pytest.raises(ValidationError, match="isin"):
            IndexMember(**{**self._VALID, "isin": "de0007164600"})

    def test_invalid_isin_wrong_format(self):
        with pytest.raises(ValidationError, match="isin"):
            IndexMember(**{**self._VALID, "isin": "123456789012"})

    def test_missing_instrument_url_raises(self):
        data = {k: v for k, v in self._VALID.items() if k != "instrument_url"}
        with pytest.raises(ValidationError, match="instrument_url"):
            IndexMember(**data)

    def test_model_dump_contains_all_fields(self):
        member = IndexMember(**self._VALID)
        dumped = member.model_dump()
        assert dumped["isin"] == "DE0007164600"
        assert dumped["asset_class"] == "Stock"
        assert dumped["instrument_url"] == "/v1/instruments/DE0007164600"
