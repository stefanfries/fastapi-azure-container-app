from fastapi import APIRouter

router = APIRouter()


@router.post("/users", tags=["users"])
async def reply_user(user: str):
    return {"message": f"Welcome {user} to this fantastic app!"}
