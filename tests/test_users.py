from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_user_self() -> None:
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome FAKEUSER to this fantastic app!"}


def test_get_user() -> None:
    response = client.get("/users/{name}")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome {name} to this fantastic app!"}
