"""Unit tests for the OpenFIGI search API client (app.clients.openfigi)."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.clients import openfigi


def _mock_async_client(response: MagicMock) -> MagicMock:
    """Build a MagicMock standing in for httpx.AsyncClient as a context manager."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=response)))
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


class TestSearchByName:
    async def test_returns_data_records(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": [{"ticker": "ASME", "exchCode": "GY", "name": "ASML HOLDING NV"}]
        }
        with patch(
            "app.clients.openfigi.httpx.AsyncClient", return_value=_mock_async_client(response)
        ):
            result = await openfigi.search_by_name("ASML HOLDING NV", exch_code="GY")

        assert result == [{"ticker": "ASME", "exchCode": "GY", "name": "ASML HOLDING NV"}]

    async def test_sends_query_and_filters(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        post_mock = AsyncMock(return_value=response)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=post_mock))
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.clients.openfigi.httpx.AsyncClient", return_value=ctx):
            await openfigi.search_by_name("ASML HOLDING NV", exch_code="GY")

        # Verify the POST body carried the query, common-stock filter, and exchange.
        _, kwargs = post_mock.call_args
        assert kwargs["json"] == {
            "query": "ASML HOLDING NV",
            "securityType2": "Common Stock",
            "exchCode": "GY",
        }

    async def test_omits_exch_code_when_not_given(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        post_mock = AsyncMock(return_value=response)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=post_mock))
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.clients.openfigi.httpx.AsyncClient", return_value=ctx):
            await openfigi.search_by_name("ASML HOLDING NV")

        _, kwargs = post_mock.call_args
        assert "exchCode" not in kwargs["json"]

    async def test_returns_empty_on_warning(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"warning": "No identifier found."}
        with patch(
            "app.clients.openfigi.httpx.AsyncClient", return_value=_mock_async_client(response)
        ):
            result = await openfigi.search_by_name("NOPE", exch_code="GY")

        assert result == []

    async def test_returns_empty_on_error(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"error": "boom"}
        with patch(
            "app.clients.openfigi.httpx.AsyncClient", return_value=_mock_async_client(response)
        ):
            result = await openfigi.search_by_name("X", exch_code="GY")

        assert result == []

    async def test_returns_empty_on_rate_limit(self) -> None:
        response = MagicMock()
        response.status_code = 429
        with patch(
            "app.clients.openfigi.httpx.AsyncClient", return_value=_mock_async_client(response)
        ):
            result = await openfigi.search_by_name("X", exch_code="GY")

        assert result == []
