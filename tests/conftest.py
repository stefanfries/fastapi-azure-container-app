"""
Shared pytest fixtures for the FinHub API test suite.

Fixture scopes:
- mock_database: session-scoped async mock for the MongoDB database — use in
  unit tests to avoid real Atlas connections.
- client: function-scoped TestClient with the database dependency patched out —
  suitable for endpoint tests that must not hit a real database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def mock_database():
    """
    Return a MagicMock that mimics an AsyncDatabase instance.

    Key async methods (find, find_one, insert_one, update_one, delete_one,
    command) are pre-configured as AsyncMocks so they can be awaited in tests.
    Override return values per-test as needed:

        mock_database.find_one.return_value = {"wkn": "716460", ...}
    """
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    db.__getitem__ = MagicMock(
        return_value=MagicMock(
            find_one=AsyncMock(return_value=None),
            find=MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[]))),
            insert_one=AsyncMock(return_value=MagicMock(inserted_id="fake_id")),
            update_one=AsyncMock(return_value=MagicMock(modified_count=1)),
            delete_one=AsyncMock(return_value=MagicMock(deleted_count=1)),
        )
    )
    return db


@pytest.fixture(scope="module")
def client(mock_database):
    """
    FastAPI TestClient with the MongoDB database patched to mock_database.

    Module-scoped: the app is started once per test module (file) rather than
    once per test, which avoids repeated lifespan startup overhead.

    Patches both connect_to_database (no-op on startup) and get_database
    (returns mock_database) so no real Atlas connection is made.

    Usage:
        def test_something(client):
            response = client.get("/v1/instruments/716460")
            assert response.status_code == 200
    """
    with (
        patch("app.main.connect_to_database", new_callable=AsyncMock),
        patch("app.main.close_database_connection", new_callable=AsyncMock),
        patch("app.core.database.get_database", return_value=mock_database),
    ):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as test_client:
            yield test_client
