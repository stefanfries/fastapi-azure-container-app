"""Unit tests for app.routers.history — GET /v1/history/{instrument_id}."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.models.history import HistoryData


def _history_data() -> HistoryData:
    return HistoryData(
        name="NVIDIA",
        wkn="918422",
        id_notation="12345",
        trading_venue="Xetra",
        currency="EUR",
        start=datetime(2024, 1, 1),
        end=datetime(2024, 12, 31),
        interval="day",
        data=[],
    )


class TestGetHistoryData:
    def test_returns_200_with_data(self, client):
        with patch(
            "app.routers.history.parse_history_data",
            new_callable=AsyncMock,
            return_value=_history_data(),
        ):
            response = client.get("/v1/history/918422", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        body = response.json()
        assert body["wkn"] == "918422"
        assert body["trading_venue"] == "Xetra"

    def test_passes_query_params(self, client):
        with patch(
            "app.routers.history.parse_history_data",
            new_callable=AsyncMock,
            return_value=_history_data(),
        ) as mock_fn:
            client.get(
                "/v1/history/918422?interval=week",
                headers={"X-API-Key": "test"},
            )
        mock_fn.assert_awaited_once()
        _, kwargs = mock_fn.call_args
        assert kwargs.get("interval") == "week" or mock_fn.call_args[1].get("interval") == "week"
