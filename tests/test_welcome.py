from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_welcome() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome, the app is live!"}


def test_get_welcome_invalid_method() -> None:
    response = client.post("/")
    assert response.status_code == 405


def test_get_welcome_not_found() -> None:
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
