"""Unit tests for app.routers.root — the root endpoint ("/")."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_welcome() -> None:
    """Root endpoint returns structured application metadata."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["application"] == "FinHub API"
    assert body["api_version"] == "v1"
    assert "version" in body
    assert "docs" in body
    assert "health" in body


def test_get_welcome_invalid_method() -> None:
    """POST to the root endpoint returns 405 Method Not Allowed."""
    response = client.post("/")
    assert response.status_code == 405


def test_get_welcome_not_found() -> None:
    """GET to an unknown endpoint returns 404 Not Found."""
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
