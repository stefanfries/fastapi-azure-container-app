"""
Low-level HTTP scraping utilities for comdirect instrument pages.

Functions:
    compose_url: Build a comdirect URL for a given instrument identifier, asset class, and id_notation.
    fetch_one:   Perform a single GET request to a composed comdirect URL and return the response.
"""

from urllib.parse import urlencode, urljoin

import httpx

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL, SEARCH_PATH
from app.core.logging import logger
from app.models.instruments import AssetClass


def compose_url(
    instrument_id: str,
    asset_class: AssetClass | None = None,
    id_notation: str | None = None,
) -> str:
    """Build a comdirect URL for the given instrument identifier, asset class, and id_notation."""

    if asset_class is None:
        return f"{BASE_URL}{SEARCH_PATH}?SEARCH_VALUE={instrument_id}"
    else:
        path = ASSET_CLASS_DETAILS_PATH.get(asset_class, SEARCH_PATH)
        params = {"SEARCH_VALUE": instrument_id}
        if id_notation:
            params["ID_NOTATION"] = id_notation
        base_url = urljoin(BASE_URL, path)
        query_string = urlencode(params)
        url = f"{base_url}?{query_string}"
        logger.debug("Composed URL: %s", url)
        return url


async def fetch_one(
    instrument_id: str,
    asset_class: AssetClass | None = None,
    id_notation: str | None = None,
) -> httpx.Response:
    """Perform a single GET request to a composed comdirect URL and return the response.

    Raises:
        httpx.HTTPStatusError: If the HTTP request returned an unsuccessful status code.
    """

    logger.debug("fetch_one(%s, asset_class=%s, id_notation=%s)", instrument_id, asset_class, id_notation)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        url = compose_url(instrument_id, asset_class, id_notation)
        response = await client.get(url)
        response.raise_for_status()
    logger.debug("fetch_one(%s) done -> HTTP %s", instrument_id, response.status_code)
    return response
