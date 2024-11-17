from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def reply_myself():
    return {"message": f"Welcome FAKEUSER to this fantastic app!"}


@router.get("/{user}")
async def reply_user(user: str):
    return {"message": f"Welcome {user} to this fantastic app!"}
