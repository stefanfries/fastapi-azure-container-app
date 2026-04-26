"""Unit tests for app.routers.quotes — GET /v1/quotes/{instrument_id}."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.models.quotes import Quote


def _quote() -> Quote:
    return Quote(
        name="NVIDIA",
        wkn="918422",
        bid=100.0,
        ask=100.1,
        spread_percent=0.1,
        currency="USD",
        timestamp=datetime(2024, 1, 1, 12, 0),
        trading_venue="Xetra",
        id_notation="12345",
    )


class TestGetQuote:
    def test_returns_200_with_quote(self, client):
        with patch(
            "app.routers.quotes.parse_quote",
            new_callable=AsyncMock,
            return_value=_quote(),
        ):
            response = client.get("/v1/quotes/918422", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        body = response.json()
        assert body["wkn"] == "918422"
        assert body["bid"] == 100.0

    def test_id_notation_query_param_passed(self, client):
        with patch(
            "app.routers.quotes.parse_quote",
            new_callable=AsyncMock,
            return_value=_quote(),
        ) as mock_fn:
            client.get(
                "/v1/quotes/918422?id_notation=12345",
                headers={"X-API-Key": "test"},
            )
        mock_fn.assert_awaited_once_with("918422", "12345")
