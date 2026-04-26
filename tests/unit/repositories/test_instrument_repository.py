"""
Unit tests for app.repositories.instruments.InstrumentRepository.

All MongoDB interactions are mocked — no real Atlas connection required.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.instruments import AssetClass, Instrument
from app.repositories.instruments import InstrumentRepository


def _make_instrument(**overrides) -> Instrument:
    defaults = dict(
        name="NVIDIA Corporation",
        wkn="918422",
        isin="US67066G1040",
        asset_class=AssetClass.STOCK,
    )
    defaults.update(overrides)
    return Instrument(**defaults)


@pytest.fixture
def collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.count_documents = AsyncMock(return_value=0)
    return col


@pytest.fixture
def repo(collection):
    r = InstrumentRepository()
    with patch("app.repositories.instruments.get_collection", return_value=collection):
        _ = r.collection
    return r


# --- find_by_wkn ---

async def test_find_by_wkn_returns_instrument(repo, collection):
    instrument = _make_instrument()
    doc = instrument.model_dump()
    doc["_id"] = "mongo_id"
    doc["cached_at"] = datetime.now(UTC)
    collection.find_one.return_value = doc

    result = await repo.find_by_wkn("918422")

    collection.find_one.assert_awaited_once_with({"wkn": "918422"})
    assert result is not None
    assert result.wkn == "918422"
    assert result.name == "NVIDIA Corporation"


async def test_find_by_wkn_strips_mongo_fields(repo, collection):
    """_id and cached_at must not be passed to Instrument()."""
    instrument = _make_instrument()
    doc = instrument.model_dump()
    doc["_id"] = "some_id"
    doc["cached_at"] = datetime.now(UTC)
    collection.find_one.return_value = doc

    result = await repo.find_by_wkn("918422")
    assert result is not None  # would raise if _id was passed to Pydantic


async def test_find_by_wkn_not_found(repo, collection):
    collection.find_one.return_value = None
    assert await repo.find_by_wkn("000000") is None


# --- find_by_isin ---

async def test_find_by_isin_returns_instrument(repo, collection):
    instrument = _make_instrument()
    doc = instrument.model_dump()
    collection.find_one.return_value = doc

    result = await repo.find_by_isin("US67066G1040")

    collection.find_one.assert_awaited_once_with({"isin": "US67066G1040"})
    assert result is not None
    assert result.isin == "US67066G1040"


async def test_find_by_isin_not_found(repo, collection):
    collection.find_one.return_value = None
    assert await repo.find_by_isin("XX0000000000") is None


# --- save ---

async def test_save_calls_upsert(repo, collection):
    instrument = _make_instrument()
    await repo.save(instrument)

    collection.update_one.assert_awaited_once()
    call_args = collection.update_one.call_args
    assert call_args[0][0] == {"wkn": "918422"}   # filter
    assert "$set" in call_args[0][1]               # update op
    assert call_args[1]["upsert"] is True


async def test_save_adds_cached_at(repo, collection):
    instrument = _make_instrument()
    await repo.save(instrument)

    doc_set = collection.update_one.call_args[0][1]["$set"]
    assert "cached_at" in doc_set


# --- is_cache_valid ---

async def test_cache_valid_when_recent(repo, collection):
    collection.find_one.return_value = {"cached_at": datetime.now(UTC)}
    assert await repo.is_cache_valid("918422", max_age_days=7) is True


async def test_cache_invalid_when_old(repo, collection):
    old_time = datetime.now(UTC) - timedelta(days=10)
    collection.find_one.return_value = {"cached_at": old_time}
    assert await repo.is_cache_valid("918422", max_age_days=7) is False


async def test_cache_invalid_when_no_doc(repo, collection):
    collection.find_one.return_value = None
    assert await repo.is_cache_valid("missing", max_age_days=7) is False


async def test_cache_invalid_when_no_cached_at(repo, collection):
    collection.find_one.return_value = {"wkn": "918422"}
    assert await repo.is_cache_valid("918422") is False


# --- delete_by_wkn ---

async def test_delete_returns_true_on_success(repo, collection):
    collection.delete_one.return_value = MagicMock(deleted_count=1)
    assert await repo.delete_by_wkn("918422") is True


async def test_delete_returns_false_when_not_found(repo, collection):
    collection.delete_one.return_value = MagicMock(deleted_count=0)
    assert await repo.delete_by_wkn("missing") is False


# --- count ---

async def test_count_returns_zero(repo, collection):
    collection.count_documents.return_value = 0
    assert await repo.count() == 0


async def test_count_returns_positive(repo, collection):
    collection.count_documents.return_value = 42
    assert await repo.count() == 42
