"""
Module to define a router for the users endpoints
"""

# The code defines a router object that includes two GET endpoints.
# The first endpoint is /users/me, which returns a welcome message for the user.
# The second endpoint is /users/{user}, which returns a welcome message for the user
# specified in the URL path.
# Both endpoints log a message using the logger object when they are called.

from fastapi import APIRouter

from app.applog import logger

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def reply_myself():
    """Reply with a welcome message for the user"""
    logger.info("Welcome FAKEUSER to this fantastic app!")

    return {"message": "Welcome FAKEUSER to this fantastic app!"}


@router.get("/{user}")
async def reply_user(user: str):
    """Reply with a welcome message for the user"""

    logger.info("Hi {user}, you have been logged!")
    return {"message": f"Welcome {user} to this fantastic app!"}
