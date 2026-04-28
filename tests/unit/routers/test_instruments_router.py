"""Unit tests for app.routers.instruments — GET /v1/instruments/ and GET /v1/instruments/{instrument_id}."""

from unittest.mock import AsyncMock, patch

from app.models.instruments import AssetClass, Instrument


def _instrument(**overrides) -> Instrument:
    defaults = dict(
        name="NVIDIA Corporation",
        wkn="918422",
        isin="US67066G1040",
        asset_class=AssetClass.STOCK,
    )
    defaults.update(overrides)
    return Instrument(**defaults)


# ---------------------------------------------------------------------------
# GET /v1/instruments/
# ---------------------------------------------------------------------------

class TestListInstruments:
    def test_returns_200_with_empty_list(self, client):
        with patch("app.routers.instruments._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            response = client.get("/v1/instruments/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_list_of_instruments(self, client):
        with patch("app.routers.instruments._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [_instrument()]
            response = client.get("/v1/instruments/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["wkn"] == "918422"

    def test_no_asset_class_passes_none_to_repo(self, client):
        with patch("app.routers.instruments._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            client.get("/v1/instruments/", headers={"X-API-Key": "test"})
        mock_find.assert_awaited_once_with(asset_class=None)

    def test_asset_class_filter_passed_to_repo(self, client):
        with patch("app.routers.instruments._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [_instrument()]
            response = client.get(
                "/v1/instruments/?asset_class=Stock", headers={"X-API-Key": "test"}
            )
        assert response.status_code == 200
        mock_find.assert_awaited_once_with(asset_class="Stock")

    def test_invalid_asset_class_returns_422(self, client):
        response = client.get(
            "/v1/instruments/?asset_class=Banana", headers={"X-API-Key": "test"}
        )


# ---------------------------------------------------------------------------
# GET /v1/instruments/{instrument_id}
# ---------------------------------------------------------------------------

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
