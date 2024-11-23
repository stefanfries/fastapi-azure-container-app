from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_welcome() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome, the app is live!"}
