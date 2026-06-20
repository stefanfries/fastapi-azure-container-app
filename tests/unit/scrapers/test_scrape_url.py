"""Unit tests for app.scrapers.scrape_url."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.instruments import AssetClass
from app.scrapers.scrape_url import compose_url, fetch_one


class TestComposeUrl:
    def test_no_asset_class_returns_search_url(self) -> None:
        url = compose_url("DE0007164600")
        assert "SEARCH_VALUE=DE0007164600" in url
        assert "search" in url

    def test_with_asset_class_returns_detail_url(self) -> None:
        url = compose_url("DE0007164600", AssetClass.STOCK)
        assert "aktien" in url
        assert "SEARCH_VALUE=DE0007164600" in url

    def test_with_asset_class_and_id_notation(self) -> None:
        url = compose_url("DE0007164600", AssetClass.STOCK, id_notation="12345")
        assert "ID_NOTATION=12345" in url
        assert "SEARCH_VALUE=DE0007164600" in url

    def test_without_id_notation_omits_parameter(self) -> None:
        url = compose_url("DE0007164600", AssetClass.ETF)
        assert "ID_NOTATION" not in url

    def test_instrument_id_encoded_in_url(self) -> None:
        url = compose_url("BASF11", AssetClass.WARRANT)
        assert "BASF11" in url


class TestFetchOne:
    async def test_fetch_one_returns_response_on_success(self, mocker) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("app.scrapers.scrape_url.httpx.AsyncClient", return_value=mock_client)

        response = await fetch_one("DE0007164600", AssetClass.STOCK)
        assert response.status_code == 200

    async def test_fetch_one_without_asset_class(self, mocker) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("app.scrapers.scrape_url.httpx.AsyncClient", return_value=mock_client)

        response = await fetch_one("DE0007164600")
        assert response is mock_response

    async def test_fetch_one_raises_on_http_error(self, mocker) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404", request=MagicMock(), response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("app.scrapers.scrape_url.httpx.AsyncClient", return_value=mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_one("INVALID", AssetClass.STOCK)
