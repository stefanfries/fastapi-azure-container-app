from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_user_me() -> None:
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome USER to this fantastic app!"}


def test_get_user() -> None:
    user = "testuser"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}


def test_get_user_with_special_characters() -> None:
    user = "test_user_123"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}


def test_get_user_with_spaces() -> None:
    user = "test user"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}
