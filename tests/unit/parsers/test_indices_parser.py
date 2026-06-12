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


# ---------------------------------------------------------------------------
# _resolve_adr_members — ADR swap / omit logic
# ---------------------------------------------------------------------------


def _member(name: str, isin: str) -> IndexMember:
    return IndexMember(
        name=name,
        isin=isin,
        link=f"/inf/aktien/{isin}",
        instrument_url=f"/v1/instruments/{isin}",
    )


async def test_resolve_adr_members_no_adr_names_is_noop():
    from app.parsers.indices import _resolve_adr_members

    members = [_member("ASML Holding", "NL0010273215"), _member("SAP", "DE0007164600")]
    # No name looks like an ADR → resolver must not be called.
    with patch("app.parsers.indices.resolve_member_isin", new_callable=AsyncMock) as mock_resolve:
        result = await _resolve_adr_members(members)

    assert result == members
    mock_resolve.assert_not_awaited()


async def test_resolve_adr_members_swaps_isin_for_resolved_adr():
    from app.parsers.indices import _resolve_adr_members

    members = [
        _member("SAP", "DE0007164600"),
        _member("ASML ADR", "USN070592100"),
    ]
    with patch(
        "app.parsers.indices.resolve_member_isin",
        new=AsyncMock(return_value="NL0010273215"),
    ):
        result = await _resolve_adr_members(members)

    assert len(result) == 2
    adr = next(m for m in result if m.name == "ASML ADR")
    assert adr.isin == "NL0010273215"
    assert adr.instrument_url == "/v1/instruments/NL0010273215"
    # Non-ADR member untouched.
    assert result[0].isin == "DE0007164600"


async def test_resolve_adr_members_omits_unresolvable_adr():
    from app.parsers.indices import _resolve_adr_members

    members = [
        _member("SAP", "DE0007164600"),
        _member("BIONTECH ADR", "US09075V1026"),
    ]
    with patch(
        "app.parsers.indices.resolve_member_isin",
        new=AsyncMock(return_value=None),
    ):
        result = await _resolve_adr_members(members)

    assert [m.name for m in result] == ["SAP"]


async def test_resolve_adr_members_keeps_adr_when_isin_unchanged():
    """If the resolver returns the same ISIN, the member is kept as-is."""
    from app.parsers.indices import _resolve_adr_members

    members = [_member("FOO ADR", "US1234567899")]
    with patch(
        "app.parsers.indices.resolve_member_isin",
        new=AsyncMock(return_value="US1234567899"),
    ):
        result = await _resolve_adr_members(members)

    assert len(result) == 1
    assert result[0].isin == "US1234567899"
    assert result[0].instrument_url == "/v1/instruments/US1234567899"
