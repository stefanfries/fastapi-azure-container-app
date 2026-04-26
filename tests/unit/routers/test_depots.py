"""
Unit tests for app.routers.depots — GET /v1/depots/ and GET /v1/depots/{id}.

Uses the shared `client` fixture which patches out the MongoDB connection.
The depot repository is patched at the router level so no real DB is needed.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.depots import Depot


def _make_depot(**overrides) -> Depot:
    defaults = dict(
        id="depot-1",
        name="My Portfolio",
        items=[],
        cash=10000.0,
        created_at=datetime(2024, 1, 1),
        changed_at=datetime(2024, 1, 1),
    )
    defaults.update(overrides)
    return Depot(**defaults)


# ---------------------------------------------------------------------------
# GET /v1/depots/
# ---------------------------------------------------------------------------

class TestGetAllDepots:
    def test_returns_200_with_empty_list(self, client):
        with patch("app.routers.depots._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            response = client.get("/v1/depots/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_list_of_depots(self, client):
        depot = _make_depot()
        with patch("app.routers.depots._repo.find_all", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [depot]
            response = client.get("/v1/depots/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "depot-1"
        assert data[0]["name"] == "My Portfolio"


# ---------------------------------------------------------------------------
# GET /v1/depots/{depot_id}
# ---------------------------------------------------------------------------

class TestGetDepotById:
    def test_returns_depot_when_found(self, client):
        depot = _make_depot()
        with patch("app.routers.depots._repo.find_by_id", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = depot
            response = client.get("/v1/depots/depot-1", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        assert response.json()["id"] == "depot-1"

    def test_returns_404_when_not_found(self, client):
        with patch("app.routers.depots._repo.find_by_id", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            response = client.get("/v1/depots/missing", headers={"X-API-Key": "test"})
        assert response.status_code == 404
        assert "missing" in response.json()["detail"]

    def test_id_in_not_found_detail(self, client):
        with patch("app.routers.depots._repo.find_by_id", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            response = client.get("/v1/depots/unknown-id")
        assert response.status_code == 404
        assert "unknown-id" in response.json()["detail"]
