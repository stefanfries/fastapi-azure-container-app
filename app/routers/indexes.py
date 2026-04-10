from fastapi import APIRouter

from app.core.logging import logger
from app.models.indexes import IndexInfo, IndexMember
from app.parsers.indexes import fetch_index_list, fetch_index_members

router = APIRouter(prefix="/v1/indexes", tags=["indexes"])


@router.get("/", response_model=list[IndexInfo])
async def get_indexes() -> list[IndexInfo]:
    """Return all supported indices (name, WKN, member count, link)."""
    logger.info("Fetching index list")
    return await fetch_index_list()


@router.get("/{index_name}", response_model=list[IndexMember])
async def get_index_members(index_name: str) -> list[IndexMember]:
    """Return all members of the named index, e.g. DAX or S&P 500."""
    logger.info("Fetching members for index '%s'", index_name)
    return await fetch_index_members(index_name)
