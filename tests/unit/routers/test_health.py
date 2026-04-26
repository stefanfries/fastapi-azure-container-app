"""
Unit tests for app.routers.health — liveness and readiness endpoints.

Mocks MongoDB ping and httpx HEAD request so no real connections are made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(mock_db=None):
    """Return a TestClient with database patched."""
    if mock_db is None:
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
    with (
        patch("app.core.database.connect_to_database", new_callable=AsyncMock),
        patch("app.core.database.close_database_connection", new_callable=AsyncMock),
        patch("app.core.database.get_database", return_value=mock_db),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# /health  (liveness)
# ---------------------------------------------------------------------------

class TestLiveness:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_healthy(self, client):
        assert client.get("/health").json()["status"] == "healthy"

    def test_has_timestamp(self, client):
        body = client.get("/health").json()
        assert "timestamp" in body


# ---------------------------------------------------------------------------
# /health/ready  (readiness — all healthy)
# ---------------------------------------------------------------------------

class TestReadinessAllHealthy:
    def test_returns_200_when_all_pass(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("app.routers.health.get_database") as mock_get_db,
            patch("app.routers.health.httpx.AsyncClient") as mock_http,
        ):
            mock_db = MagicMock()
            mock_db.command = AsyncMock(return_value={"ok": 1})
            mock_get_db.return_value = mock_db

            mock_async_ctx = MagicMock()
            mock_async_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
                head=AsyncMock(return_value=mock_response)
            ))
            mock_async_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = mock_async_ctx

            response = client.get("/health/ready")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"] == "healthy"
        assert body["checks"]["comdirect_access"] == "healthy"

    def test_has_version(self, client):
        with (
            patch("app.routers.health.get_database") as mock_get_db,
            patch("app.routers.health.httpx.AsyncClient") as mock_http,
        ):
            mock_db = MagicMock()
            mock_db.command = AsyncMock(return_value={"ok": 1})
            mock_get_db.return_value = mock_db
            mock_async_ctx = MagicMock()
            mock_async_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
                head=AsyncMock(return_value=MagicMock(status_code=200))
            ))
            mock_async_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = mock_async_ctx

            body = client.get("/health/ready").json()
        assert "version" in body


# ---------------------------------------------------------------------------
# /health/ready  (readiness — database failure)
# ---------------------------------------------------------------------------

class TestReadinessDatabaseFailure:
    def test_returns_503_when_db_fails(self, client):
        with (
            patch("app.routers.health.get_database") as mock_get_db,
            patch("app.routers.health.httpx.AsyncClient") as mock_http,
        ):
            mock_db = MagicMock()
            mock_db.command = AsyncMock(side_effect=Exception("connection refused"))
            mock_get_db.return_value = mock_db
            mock_async_ctx = MagicMock()
            mock_async_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
                head=AsyncMock(return_value=MagicMock(status_code=200))
            ))
            mock_async_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = mock_async_ctx

            response = client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["checks"]["database"] == "unhealthy"
        assert response.json()["status"] == "not ready"


# ---------------------------------------------------------------------------
# /health/ready  (readiness — comdirect unreachable)
# ---------------------------------------------------------------------------

class TestReadinessComdirectFailure:
    def test_returns_503_when_comdirect_fails(self, client):
        with (
            patch("app.routers.health.get_database") as mock_get_db,
            patch("app.routers.health.httpx.AsyncClient") as mock_http,
        ):
            mock_db = MagicMock()
            mock_db.command = AsyncMock(return_value={"ok": 1})
            mock_get_db.return_value = mock_db
            mock_async_ctx = MagicMock()
            mock_async_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
                head=AsyncMock(side_effect=Exception("timeout"))
            ))
            mock_async_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = mock_async_ctx

            response = client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["checks"]["comdirect_access"] == "unhealthy"
