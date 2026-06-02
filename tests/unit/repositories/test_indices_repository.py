"""Unit tests for app.repositories.indices.IndicesRepository.

All MongoDB interactions are mocked — no real Atlas connection required.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.indices import IndexInfo, IndexMember
from app.repositories.indices import IndicesRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_index_info(**overrides) -> IndexInfo:
    defaults = dict(name="DAX", isin="DE0008469008", member_count=40, link="/inf/indizes/DE0008469008")
    defaults.update(overrides)
    return IndexInfo(**defaults)


def _make_member(**overrides) -> IndexMember:
    defaults = dict(
        name="NVIDIA",
        isin="US67066G1040",
        link="/inf/aktien/nvidia",
        instrument_url="/v1/instruments/US67066G1040",
    )
    defaults.update(overrides)
    return IndexMember(**defaults)


def _doc_from_index(index: IndexInfo, age: timedelta = timedelta(hours=1)) -> dict:
    doc = index.model_dump()
    doc["cached_at"] = datetime.now(UTC) - age
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def catalogue_col():
    col = MagicMock()
    col.find = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    return col


@pytest.fixture
def members_col():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    return col


@pytest.fixture
def repo(catalogue_col, members_col):
    r = IndicesRepository()
    with patch("app.repositories.indices.get_collection", side_effect=lambda name: {
        "index_catalogue": catalogue_col,
        "index_members": members_col,
    }[name]):
        _ = r.catalogue
        _ = r.members
    return r


def _mock_find(col, docs: list[dict]) -> None:
    """Wire col.find(...).to_list() to return *docs*."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=docs)
    col.find.return_value = cursor


# ---------------------------------------------------------------------------
# IndicesRepository._is_fresh
# ---------------------------------------------------------------------------

def test_is_fresh_recent(repo):
    assert repo._is_fresh(datetime.now(UTC) - timedelta(hours=1)) is True


def test_is_fresh_stale(repo):
    with patch("app.repositories.indices.get_settings") as mock_settings:
        mock_settings.return_value.cache.index_cache_ttl_days = 3
        assert repo._is_fresh(datetime.now(UTC) - timedelta(days=4)) is False


def test_is_fresh_naive_datetime_treated_as_utc(repo):
    """MongoDB returns naive datetimes; _is_fresh must not raise TypeError."""
    recent_naive = datetime.now() - timedelta(hours=1)
    assert repo._is_fresh(recent_naive) is True


# ---------------------------------------------------------------------------
# IndicesRepository.get_catalogue
# ---------------------------------------------------------------------------

async def test_get_catalogue_returns_none_when_empty(repo, catalogue_col):
    _mock_find(catalogue_col, [])
    result = await repo.get_catalogue()
    assert result is None


async def test_get_catalogue_returns_none_when_stale(repo, catalogue_col):
    index = _make_index_info()
    stale_doc = _doc_from_index(index, age=timedelta(days=5))
    # First find (projection -_id -cached_at) returns the data docs
    # Second find (projection cached_at only) returns docs with stale cached_at
    cursor_data = MagicMock()
    cursor_data.to_list = AsyncMock(return_value=[stale_doc])
    cursor_stale = MagicMock()
    cursor_stale.to_list = AsyncMock(return_value=[stale_doc])
    catalogue_col.find.side_effect = [cursor_data, cursor_stale]

    with patch("app.repositories.indices.get_settings") as mock_settings:
        mock_settings.return_value.cache.index_cache_ttl_days = 3
        result = await repo.get_catalogue()

    assert result is None


async def test_get_catalogue_returns_entries_when_fresh(repo, catalogue_col):
    index = _make_index_info()
    fresh_doc = _doc_from_index(index, age=timedelta(hours=2))

    cursor_data = MagicMock()
    cursor_data.to_list = AsyncMock(return_value=[fresh_doc])
    cursor_stale = MagicMock()
    cursor_stale.to_list = AsyncMock(return_value=[fresh_doc])
    catalogue_col.find.side_effect = [cursor_data, cursor_stale]

    with patch("app.repositories.indices.get_settings") as mock_settings:
        mock_settings.return_value.cache.index_cache_ttl_days = 3
        result = await repo.get_catalogue()

    assert result is not None
    assert len(result) == 1
    assert result[0].name == "DAX"


# ---------------------------------------------------------------------------
# IndicesRepository.save_catalogue
# ---------------------------------------------------------------------------

async def test_save_catalogue_upserts_each_index(repo, catalogue_col):
    indices = [_make_index_info(), _make_index_info(name="MDAX", isin="DE0008467416")]
    await repo.save_catalogue(indices)

    assert catalogue_col.update_one.await_count == 2


async def test_save_catalogue_adds_cached_at(repo, catalogue_col):
    await repo.save_catalogue([_make_index_info()])

    doc_set = catalogue_col.update_one.call_args[0][1]["$set"]
    assert "cached_at" in doc_set


async def test_save_catalogue_uses_isin_as_key(repo, catalogue_col):
    index = _make_index_info(isin="DE0008469008")
    await repo.save_catalogue([index])

    filter_arg = catalogue_col.update_one.call_args[0][0]
    assert filter_arg == {"isin": "DE0008469008"}


# ---------------------------------------------------------------------------
# IndicesRepository.get_members
# ---------------------------------------------------------------------------

async def test_get_members_returns_none_when_not_found(repo, members_col):
    members_col.find_one.return_value = None
    result = await repo.get_members("DE0008469008")
    assert result is None


async def test_get_members_returns_none_when_stale(repo, members_col):
    member = _make_member()
    members_col.find_one.return_value = {
        "isin": "DE0008469008",
        "members": [member.model_dump()],
        "cached_at": datetime.now(UTC) - timedelta(days=5),
    }

    with patch("app.repositories.indices.get_settings") as mock_settings:
        mock_settings.return_value.cache.index_cache_ttl_days = 3
        result = await repo.get_members("DE0008469008")

    assert result is None


async def test_get_members_returns_list_when_fresh(repo, members_col):
    member = _make_member()
    members_col.find_one.return_value = {
        "isin": "DE0008469008",
        "members": [member.model_dump()],
        "cached_at": datetime.now(UTC) - timedelta(hours=1),
    }

    with patch("app.repositories.indices.get_settings") as mock_settings:
        mock_settings.return_value.cache.index_cache_ttl_days = 3
        result = await repo.get_members("DE0008469008")

    assert result is not None
    assert len(result) == 1
    assert result[0].isin == "US67066G1040"


async def test_get_members_queries_by_isin(repo, members_col):
    members_col.find_one.return_value = None
    await repo.get_members("DE0008469008")
    members_col.find_one.assert_awaited_once_with({"isin": "DE0008469008"})


# ---------------------------------------------------------------------------
# IndicesRepository.save_members
# ---------------------------------------------------------------------------

async def test_save_members_upserts_with_isin_key(repo, members_col):
    members = [_make_member()]
    await repo.save_members("DE0008469008", members)

    filter_arg = members_col.update_one.call_args[0][0]
    assert filter_arg == {"isin": "DE0008469008"}
    assert members_col.update_one.call_args[1]["upsert"] is True


async def test_save_members_stores_serialised_members(repo, members_col):
    members = [_make_member()]
    await repo.save_members("DE0008469008", members)

    doc_set = members_col.update_one.call_args[0][1]["$set"]
    assert "members" in doc_set
    assert len(doc_set["members"]) == 1
    assert doc_set["members"][0]["isin"] == "US67066G1040"


async def test_save_members_adds_cached_at(repo, members_col):
    await repo.save_members("DE0008469008", [_make_member()])

    doc_set = members_col.update_one.call_args[0][1]["$set"]
    assert "cached_at" in doc_set
