"""Unit tests for app.routers.indices — GET /v1/indices/ and GET /v1/indices/{name}."""

from unittest.mock import AsyncMock, patch

from app.models.indices import IndexInfo, IndexMember


def _index_info() -> IndexInfo:
    return IndexInfo(name="DAX", member_count=40, link="/inf/indizes/dax")


def _index_member() -> IndexMember:
    return IndexMember(
        name="NVIDIA",
        isin="US67066G1040",
        link="/inf/aktien/nvidia",
    )


class TestGetIndices:
    def test_returns_200_with_list(self, client):
        with patch(
            "app.routers.indices.fetch_index_list",
            new_callable=AsyncMock,
            return_value=[_index_info()],
        ):
            response = client.get("/v1/indices/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "DAX"

    def test_returns_empty_list(self, client):
        with patch(
            "app.routers.indices.fetch_index_list",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/v1/indices/", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetIndexMembers:
    def test_returns_members(self, client):
        with patch(
            "app.routers.indices.fetch_index_members",
            new_callable=AsyncMock,
            return_value=[_index_member()],
        ):
            response = client.get("/v1/indices/DAX", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["isin"] == "US67066G1040"

    def test_returns_empty_list(self, client):
        with patch(
            "app.routers.indices.fetch_index_members",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/v1/indices/UNKNOWN", headers={"X-API-Key": "test"})
        assert response.status_code == 200
        assert response.json() == []
