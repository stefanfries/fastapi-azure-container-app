"""
Module to define a router for the users endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def reply_myself():
    """Reply with a welcome message for the user"""

    return {"message": "Welcome FAKEUSER to this fantastic app!"}


@router.get("/{user}")
async def reply_user(user: str):
    """Reply with a welcome message for the user"""

    return {"message": f"Welcome {user} to this fantastic app!"}


# The code defines two routes for the users endpoint. The first route is /users/me, which returns a welcome message for the user. The second route is /users/{user}, which returns a welcome message for the user specified in the URL. The user parameter is passed to the route as a path parameter.
