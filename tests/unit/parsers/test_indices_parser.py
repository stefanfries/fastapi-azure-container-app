"""Unit tests for cache-wrapping logic in app.parsers.indices.

Covers fetch_index_list and fetch_index_members cache hit/miss paths
without making real HTTP requests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.indices import IndexInfo, IndexMember
from app.parsers.indices import fetch_index_list, fetch_index_members

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_index(name: str = "DAX", isin: str = "DE0008469008") -> IndexInfo:
    return IndexInfo(
        name=name,
        isin=isin,
        member_count=40,
        link=f"/inf/indizes/dax/{isin}",
    )


def _make_member() -> IndexMember:
    return IndexMember(
        name="NVIDIA",
        isin="US67066G1040",
        link="/inf/aktien/nvidia",
        instrument_url="/v1/instruments/US67066G1040",
    )


# ---------------------------------------------------------------------------
# fetch_index_list — cache hit
# ---------------------------------------------------------------------------


async def test_fetch_index_list_returns_cache_hit():
    indices = [_make_index()]
    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=indices)
        mock_repo.save_catalogue = AsyncMock()

        result = await fetch_index_list()

    assert result == indices
    mock_repo.save_catalogue.assert_not_awaited()


# ---------------------------------------------------------------------------
# fetch_index_list — cache miss
# ---------------------------------------------------------------------------


async def test_fetch_index_list_scrapes_and_saves_on_cache_miss():
    indices = [_make_index()]
    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=None)
        mock_repo.save_catalogue = AsyncMock()

        with patch(
            "app.parsers.indices._scrape_index_list", new_callable=AsyncMock, return_value=indices
        ):
            result = await fetch_index_list()

    assert result == indices
    mock_repo.save_catalogue.assert_awaited_once_with(indices)


# ---------------------------------------------------------------------------
# fetch_index_members — catalogue cache + members cache hit
# ---------------------------------------------------------------------------


async def test_fetch_index_members_returns_members_cache_hit():
    index = _make_index()
    members = [_make_member()]

    with patch("app.parsers.indices._repo") as mock_repo:
        # catalogue cache: fresh
        mock_repo.get_catalogue = AsyncMock(return_value=[index])
        mock_repo.save_catalogue = AsyncMock()
        # members cache: hit
        mock_repo.get_members = AsyncMock(return_value=members)
        mock_repo.save_members = AsyncMock()

        result = await fetch_index_members("DAX")

    assert result == members
    mock_repo.save_members.assert_not_awaited()


# ---------------------------------------------------------------------------
# fetch_index_members — catalogue cache + members cache miss → scrape
# ---------------------------------------------------------------------------


async def test_fetch_index_members_scrapes_when_members_cache_miss():
    index = _make_index()
    members = [_make_member()]

    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=[index])
        mock_repo.save_catalogue = AsyncMock()
        mock_repo.get_members = AsyncMock(return_value=None)
        mock_repo.save_members = AsyncMock()

        with patch(
            "app.parsers.indices._fetch_all_members", new_callable=AsyncMock, return_value=members
        ):
            result = await fetch_index_members("DAX")

    assert result == members
    mock_repo.save_members.assert_awaited_once_with("DE0008469008", members)


# ---------------------------------------------------------------------------
# fetch_index_members — ISIN lookup via catalogue link
# ---------------------------------------------------------------------------


async def test_fetch_index_members_lookup_by_isin():
    index = _make_index(name="DAX", isin="DE0008469008")
    members = [_make_member()]

    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=[index])
        mock_repo.save_catalogue = AsyncMock()
        mock_repo.get_members = AsyncMock(return_value=None)
        mock_repo.save_members = AsyncMock()

        with patch(
            "app.parsers.indices._fetch_all_members", new_callable=AsyncMock, return_value=members
        ):
            result = await fetch_index_members("DE0008469008")

    assert result == members


# ---------------------------------------------------------------------------
# fetch_index_members — ISIN fallback (not in catalogue)
# ---------------------------------------------------------------------------


async def test_fetch_index_members_isin_fallback_not_in_catalogue():
    """An ISIN not found in the catalogue should still be fetched directly."""
    members = [_make_member()]

    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=[])
        mock_repo.save_catalogue = AsyncMock()
        mock_repo.get_members = AsyncMock(return_value=None)
        mock_repo.save_members = AsyncMock()

        with patch(
            "app.parsers.indices._fetch_all_members", new_callable=AsyncMock, return_value=members
        ):
            result = await fetch_index_members("DE0008469008")

    assert result == members
    mock_repo.save_members.assert_awaited_once_with("DE0008469008", members)


# ---------------------------------------------------------------------------
# fetch_index_members — ISIN fallback with members cache hit
# ---------------------------------------------------------------------------


async def test_fetch_index_members_isin_fallback_cache_hit():
    members = [_make_member()]

    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=[])
        mock_repo.save_catalogue = AsyncMock()
        mock_repo.get_members = AsyncMock(return_value=members)
        mock_repo.save_members = AsyncMock()

        result = await fetch_index_members("DE0008469008")

    assert result == members
    mock_repo.save_members.assert_not_awaited()


# ---------------------------------------------------------------------------
# fetch_index_members — unknown name → 404
# ---------------------------------------------------------------------------


async def test_fetch_index_members_unknown_name_raises_404():
    with patch("app.parsers.indices._repo") as mock_repo:
        mock_repo.get_catalogue = AsyncMock(return_value=[_make_index()])
        mock_repo.save_catalogue = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await fetch_index_members("UNKNOWN_INDEX")

    assert exc_info.value.status_code == 404
