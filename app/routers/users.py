"""
Module to define a router for the users endpoints

The code defines a router object that includes two GET endpoints.
The first endpoint is /users/me, which returns a welcome message for the user.
The second endpoint is /users/{user}, which returns a welcome message for the user
specified in the URL path.
Both endpoints log a message using the logger object when they are called.

"""

from fastapi import APIRouter

from app.applogger import logger

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_user_me():
    """Reply with a welcome message for the user"""
    logger.info("Welcome USER to this fantastic app!")
    return {"message": "Welcome USER to this fantastic app!"}


@router.get("/{user}")
async def get_user_by_name(user: str):
    """Reply with a welcome message for the user"""
    logger.info("Hi %s, you have been logged!", user)
    return {"message": f"Welcome {user} to this fantastic app!"}
