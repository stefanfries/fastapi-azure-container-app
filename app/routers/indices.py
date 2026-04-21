"""
Router for stock market index endpoints.

Provides two endpoints:
    GET /v1/indices              — list all supported indices scraped from comdirect
    GET /v1/indices/{index_name} — list all members of a named index

Functions:
    get_indices:       Return the catalogue of all supported indices.
    get_index_members: Return all constituent members of the specified index.

Dependencies:
    fastapi.APIRouter: Used to create the router for the index routes.
    app.core.logging.logger: Logger instance for logging information.
"""

from fastapi import APIRouter, Depends

from app.core.logging import logger
from app.core.security import require_api_key
from app.models.indices import IndexInfo, IndexMember
from app.parsers.indices import fetch_index_list, fetch_index_members

router = APIRouter(prefix="/v1/indices", tags=["indices"], dependencies=[Depends(require_api_key)])


@router.get("/", response_model=list[IndexInfo])
async def get_indices() -> list[IndexInfo]:
    """Return all supported indices (name, WKN, member count, link).

    Scrapes the comdirect index overview page and returns one entry per
    supported index.  WKN is fetched in parallel for each result.

    Returns:
        list[IndexInfo]: Catalogue of all supported indices.
    """
    logger.info("Fetching index list")
    return await fetch_index_list()


@router.get("/{index_name}", response_model=list[IndexMember])
async def get_index_members(index_name: str) -> list[IndexMember]:
    """Return all constituent members of the named index.

    The index name is matched case-insensitively and is normalised before
    comparison, so variants such as ``S&P 500``, ``SP500``, or ``SandP500``
    all resolve to the same index.  All pages of the paginated comdirect
    member table are fetched and merged.

    Args:
        index_name: Human-readable index name, e.g. ``DAX`` or ``S&P 500``.
                    Pass the value URL-encoded when the name contains
                    special characters (``S%26P%20500``).

    Returns:
        list[IndexMember]: All constituent members of the requested index.

    Raises:
        HTTPException 404: If no index matching *index_name* is found.
        HTTPException 502: If the ISIN cannot be determined for pagination.
    """
    logger.info("Fetching members for index '%s'", index_name)
    return await fetch_index_members(index_name)
