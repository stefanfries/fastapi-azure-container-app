"""Unit tests for cache-wrapping logic in app.parsers.indices.

Covers fetch_index_list and fetch_index_members cache hit/miss paths
without making real HTTP requests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.models.indices import IndexInfo, IndexMember
from app.parsers.indices import (
    _deduplicate_members_by_isin,
    _fetch_all_members,
    _log_member_anomalies,
    _parse_members_from_table,
    fetch_index_list,
    fetch_index_members,
)

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


def test_parse_members_applies_known_name_override():
    html = """
    <table class="table--comparison">
      <tr>
        <th><a href="/inf/aktien/detail/uebersicht.html?ID_NOTATION=1&ISIN=US74743L1008">QNITY ELECTRONICS O.N.</a></th>
      </tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")

    members = _parse_members_from_table(soup)

    assert len(members) == 1
    assert members[0].isin == "US74743L1008"
    assert members[0].name == "Bunge Global S.A."


def test_deduplicate_members_by_isin_keeps_first_entry():
    members = [
        IndexMember(
            name="First",
            isin="US74743L1008",
            link="https://example.com/1",
            instrument_url="/v1/instruments/US74743L1008",
        ),
        IndexMember(
            name="Second",
            isin="US74743L1008",
            link="https://example.com/2",
            instrument_url="/v1/instruments/US74743L1008",
        ),
    ]

    deduped = _deduplicate_members_by_isin(members, "S&P 500")

    assert len(deduped) == 1
    assert deduped[0].name == "First"


def test_log_member_anomalies_logs_duplicate_name_group():
    members = [
        IndexMember(
            name="Bunge Global S.A.",
            isin="US74743L1008",
            link="https://example.com/1",
            instrument_url="/v1/instruments/US74743L1008",
        ),
        IndexMember(
            name="Bunge Global SA",
            isin="US1234567890",
            link="https://example.com/2",
            instrument_url="/v1/instruments/US1234567890",
        ),
    ]

    with patch("app.parsers.indices.logger") as mock_logger:
        _log_member_anomalies(members, "S&P 500")

    assert mock_logger.warning.called


def test_log_member_anomalies_does_not_flag_onn_suffix_alone():
    members = [
        IndexMember(
            name="ERIE INDEMNITY CO. A O.N.",
            isin="US29530P1021",
            link="https://example.com/1",
            instrument_url="/v1/instruments/US29530P1021",
        )
    ]

    with patch("app.parsers.indices.logger") as mock_logger:
        _log_member_anomalies(members, "S&P 500")

    mock_logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_all_members_logs_count_mismatch_warning():
    html = """
    <table class="table--comparison">
      <tr>
        <th><a href="/inf/aktien/US67066G1040">NVIDIA</a></th>
      </tr>
    </table>
    """

    class FakeResponse:
        def __init__(self, body: str) -> None:
            self.content = body.encode("utf-8")

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str):
            return FakeResponse(html)

    with patch("app.parsers.indices.httpx.AsyncClient", return_value=FakeClient()), patch(
        "app.parsers.indices.logger"
    ) as mock_logger:
        members = await _fetch_all_members("US0000000001", label="S&P 500", expected_count=2)

    assert len(members) == 1
    assert members[0].isin == "US67066G1040"
    warning_messages = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("Member count mismatch" in msg for msg in warning_messages)
