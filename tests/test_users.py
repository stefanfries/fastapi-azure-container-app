from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_user_me() -> None:
    """
    Test the endpoint to get the current authenticated user's information.
    This test sends a GET request to the "/users/me" endpoint and verifies that the response status code is 200.
    It also checks that the response JSON contains the expected welcome message for the user.
    Assertions:
        - The response status code should be 200.
        - The response JSON should match {"message": "Welcome USER to this fantastic app!"}.
    """

    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome USER to this fantastic app!"}


def test_get_user() -> None:
    """
    Test the GET /users/{user} endpoint.
    This test checks if the endpoint correctly returns a welcome message
    for a given user. It verifies that the response status code is 200
    and the response JSON contains the expected welcome message.
    Assertions:
        - The response status code should be 200.
        - The response JSON should match the expected welcome message.
    """

    user = "testuser"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}


def test_get_user_with_special_characters() -> None:
    """
    Test the endpoint for retrieving a user with special characters in the username.
    This test sends a GET request to the /users/{user} endpoint with a username
    containing special characters and verifies that the response status code is 200
    and the response JSON contains the expected welcome message.
    Assertions:
        - The response status code should be 200.
        - The response JSON should contain the expected welcome message with the username.
    """

    user = "test_user_123"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}


def test_get_user_with_spaces() -> None:
    """
    Test the endpoint for retrieving a user with spaces in the username.
    This test checks if the API correctly handles usernames that contain spaces.
    It sends a GET request to the `/users/{user}` endpoint with a username that includes spaces
    and verifies that the response status code is 200 and the response JSON contains the expected message.
    Assertions:
    - The response status code should be 200.
    - The response JSON should contain a welcome message with the username.
    """

    user = "test user"
    response = client.get(f"/users/{user}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {user} to this fantastic app!"}
