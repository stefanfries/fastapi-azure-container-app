from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["welcome"])
async def read_root():
    return {"message": "Welcome to this fantastic app!"}
