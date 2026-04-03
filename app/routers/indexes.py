from typing import Optional

from fastapi import APIRouter, Query

from app.logging_config import logger
from app.models.indexes import IndexInfo, IndexMember
from app.parsers.indexes import fetch_index_list, fetch_index_members

router = APIRouter(prefix="/v1/indexes", tags=["indexes"])


@router.get("", response_model=None)
async def get_indexes(
    name: Optional[str] = Query(None, description="Index name to retrieve members for, e.g. 'DAX'"),
) -> list[IndexInfo] | list[IndexMember]:
    """
    Without parameters: return all supported indices (name, WKN, members link).
    With ?name=<index_name>: return the members of the specified index.
    """
    if name is None:
        logger.info("Fetching index list")
        return await fetch_index_list()

    logger.info("Fetching members for index '%s'", name)
    return await fetch_index_members(name)
