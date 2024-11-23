from fastapi.testclient import TestClient

from app.main import main


def test_get_user_self() -> None:
    assert main() == None


def test_get_user() -> None:
    assert main() == None
