"""Unit tests for app.routers.admin runtime log-level endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import admin


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(admin.router)
    return TestClient(app, raise_server_exceptions=True)


class TestGetLogLevel:
    def test_returns_current_runtime_level(self):
        client = _make_client()
        with patch("app.routers.admin.get_runtime_log_level", return_value="WARNING"):
            response = client.get("/v1/admin/log-level", headers={"X-API-Key": "test"})

        assert response.status_code == 200
        assert response.json() == {"log_level": "WARNING"}


class TestUpdateLogLevel:
    def test_updates_and_persists_by_default(self):
        client = _make_client()
        with (
            patch("app.routers.admin.set_runtime_log_level", return_value="ERROR") as mock_set,
            patch("app.routers.admin.persist_log_level", new_callable=AsyncMock) as mock_persist,
        ):
            response = client.put(
                "/v1/admin/log-level",
                headers={"X-API-Key": "test"},
                json={"log_level": "ERROR"},
            )

        assert response.status_code == 200
        assert response.json() == {"log_level": "ERROR"}
        mock_set.assert_called_once_with("ERROR")
        mock_persist.assert_awaited_once_with("ERROR")

    def test_updates_without_persist(self):
        client = _make_client()
        with (
            patch("app.routers.admin.set_runtime_log_level", return_value="WARNING") as mock_set,
            patch("app.routers.admin.persist_log_level", new_callable=AsyncMock) as mock_persist,
        ):
            response = client.put(
                "/v1/admin/log-level",
                headers={"X-API-Key": "test"},
                json={"log_level": "WARNING", "persist": False},
            )

        assert response.status_code == 200
        assert response.json() == {"log_level": "WARNING"}
        mock_set.assert_called_once_with("WARNING")
        mock_persist.assert_not_awaited()

    def test_rejects_invalid_log_level(self):
        client = _make_client()
        with patch(
            "app.routers.admin.set_runtime_log_level", side_effect=ValueError("bad level")
        ):
            response = client.put(
                "/v1/admin/log-level",
                headers={"X-API-Key": "test"},
                json={"log_level": "NOPE"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "bad level"

    def test_returns_503_when_persist_database_unavailable(self):
        client = _make_client()
        with (
            patch("app.routers.admin.set_runtime_log_level", return_value="INFO"),
            patch(
                "app.routers.admin.persist_log_level",
                new_callable=AsyncMock,
                side_effect=RuntimeError("db unavailable"),
            ),
        ):
            response = client.put(
                "/v1/admin/log-level",
                headers={"X-API-Key": "test"},
                json={"log_level": "INFO"},
            )

        assert response.status_code == 503
        assert response.json()["detail"] == "Database is not initialized"
