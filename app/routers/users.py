"""
Module to define a router for the users endpoints

The code defines a router object that includes two GET endpoints.
The first endpoint is /users/me, which returns a welcome message for the user.
The second endpoint is /users/{user}, which returns a welcome message for the user
specified in the URL path.
Both endpoints log a message using the logger object when they are called.

"""

from fastapi import APIRouter

from app.logging_config import logger

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_user_me():
    """
    Asynchronous function to get the current user's information.
    This function logs a welcome message and returns a welcome message
    for the user.
    Returns:
        dict: A dictionary containing a welcome message for the user.
    """

    logger.info("Welcome USER to this fantastic app!")
    return {"message": "Welcome USER to this fantastic app!"}


@router.get("/{user}")
async def get_user_by_name(user: str):
    """
    Fetch a user by their name.
    Args:
        user (str): The name of the user to fetch.
    Returns:
        dict: A dictionary containing a welcome message for the user.
    """

    logger.info("Hi %s, you have been logged!", user)
    return {"message": f"Welcome {user} to this fantastic app!"}
