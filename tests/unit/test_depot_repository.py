"""
Unit tests for DepotRepository.

All MongoDB interactions are mocked — no real Atlas connection required.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.depots import Depot
from app.repositories.depots import DepotRepository


def _make_depot(**overrides) -> Depot:
    defaults = dict(
        id="depot-1",
        name="Test Depot",
        items=[],
        cash=5000.0,
        created_at=datetime(2024, 1, 1),
        changed_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return Depot(**defaults)


@pytest.fixture
def collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    # find() returns a cursor-like object with to_list
    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[])
    col.find = MagicMock(return_value=cursor_mock)
    return col


@pytest.fixture
def repo(collection):
    r = DepotRepository()
    with patch("app.repositories.depots.get_collection", return_value=collection):
        _ = r.collection
    return r


# --- find_all ---

async def test_find_all_returns_empty_list(repo, collection):
    result = await repo.find_all()
    assert result == []


async def test_find_all_returns_depots(repo, collection):
    depot = _make_depot()
    collection.find.return_value.to_list.return_value = [depot.model_dump()]

    result = await repo.find_all()

    assert len(result) == 1
    assert result[0].id == "depot-1"


# --- find_by_id ---

async def test_find_by_id_returns_depot(repo, collection):
    depot = _make_depot()
    collection.find_one.return_value = depot.model_dump()

    result = await repo.find_by_id("depot-1")

    collection.find_one.assert_awaited_once_with({"id": "depot-1"})
    assert result is not None
    assert result.name == "Test Depot"


async def test_find_by_id_not_found(repo, collection):
    collection.find_one.return_value = None

    result = await repo.find_by_id("missing")

    assert result is None


# --- create ---

async def test_create_inserts_depot(repo, collection):
    collection.find_one.return_value = None  # no duplicate
    depot = _make_depot()

    result = await repo.create(depot)

    collection.insert_one.assert_awaited_once()
    assert result.id == "depot-1"


async def test_create_raises_on_duplicate(repo, collection):
    depot = _make_depot()
    collection.find_one.return_value = depot.model_dump()  # simulate existing

    with pytest.raises(ValueError, match="already exists"):
        await repo.create(depot)


# --- update ---

async def test_update_returns_true_on_success(repo, collection):
    result = await repo.update("depot-1", {"cash": 9999.0})
    assert result is True


async def test_update_returns_false_when_no_match(repo, collection):
    collection.update_one.return_value = MagicMock(modified_count=0)
    result = await repo.update("missing", {"cash": 0.0})
    assert result is False


# --- delete ---

async def test_delete_returns_true_on_success(repo, collection):
    result = await repo.delete("depot-1")
    assert result is True


async def test_delete_returns_false_when_not_found(repo, collection):
    collection.delete_one.return_value = MagicMock(deleted_count=0)
    result = await repo.delete("missing")
    assert result is False
