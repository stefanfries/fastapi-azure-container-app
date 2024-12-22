"""
Unit tests for the FastAPI application.
This module contains tests for the root endpoint ("/") of the FastAPI application.
The tests use the FastAPI TestClient to simulate HTTP requests and verify the responses.
Tests included:
- test_get_welcome: Verifies that a GET request to the root endpoint returns a 200 status code
    and the expected JSON response.
- test_get_welcome_invalid_method: Ensures that a POST request to the root endpoint returns
    a 405 Method Not Allowed status code.
- test_get_welcome_not_found: Checks that a GET request to an invalid endpoint returns a 404
    Not Found status code.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_welcome() -> None:
    """
    Test the GET request to the root endpoint ("/") of the FastAPI application.
    This test checks if the response status code is 200 (OK) and if the JSON response
    contains the expected message: {"message": "Welcome, the app is live!"}.
    """

    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome, the app is live!!! 🚀🚀🚀"}


def test_get_welcome_invalid_method() -> None:
    """
    Test that sending a POST request to the root endpoint returns a 405 Method Not Allowed status code.
    This test ensures that the root endpoint only allows GET requests and properly handles invalid HTTP methods.
    """

    response = client.post("/")
    assert response.status_code == 405


def test_get_welcome_not_found() -> None:
    """
    Test the GET request to an invalid endpoint.
    This test sends a GET request to an invalid endpoint and asserts that the
    response status code is 404, indicating that the resource was not found.
    """

    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
