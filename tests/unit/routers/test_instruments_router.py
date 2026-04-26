"""Unit tests for app.routers.instruments — GET /v1/instruments/{instrument_id}."""

from unittest.mock import AsyncMock, patch

from app.models.instruments import AssetClass, Instrument


def _instrument() -> Instrument:
    return Instrument(
        name="NVIDIA Corporation",
        wkn="918422",
        isin="US67066G1040",
        asset_class=AssetClass.STOCK,
    )


class TestGetInstrument:
    def test_returns_200_with_instrument(self, client):
        with patch(
            "app.routers.instruments.parse_instrument_data",
            new_callable=AsyncMock,
            return_value=_instrument(),
        ):
            response = client.get("/v1/instruments/918422", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        body = response.json()
        assert body["wkn"] == "918422"
        assert body["name"] == "NVIDIA Corporation"

    def test_instrument_id_passed_to_parser(self, client):
        with patch(
            "app.routers.instruments.parse_instrument_data",
            new_callable=AsyncMock,
            return_value=_instrument(),
        ) as mock_fn:
            client.get("/v1/instruments/US67066G1040", headers={"X-API-Key": "test"})
        mock_fn.assert_awaited_once_with("US67066G1040")
