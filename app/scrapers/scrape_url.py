from urllib.parse import urlencode, urljoin

import httpx

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL, SEARCH_PATH
from app.models.basedata import AssetClass

# from typing import AsyncGenerator, AsyncIterator, Dict, List


def compose_url(
    instrument_id: str,
    asset_class: AssetClass | None = None,
    id_notation: str | None = None,
) -> str:
    """
    Composes a URL for a given instrument ID.
    Args:
        instrument_id (str): The ID of the instrument to search for.
        asset_class (AssetClass, optional): The asset class of the instrument. Defaults to None.
        id_notation (str, optional): The ID notation of the instrument. Defaults to None.
    Returns:
        str: The composed URL.
    """

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
        print(f"Full_URL: {url}")
        return url


async def fetch_one(
    instrument_id: str,
    asset_class: AssetClass | None = None,
    id_notation: str | None = None,
) -> httpx.Response:
    """
    Fetch data from a URL composed of the given parameters.
    Args:
        instrument_id (str): The ID of the instrument to fetch data for.
        asset_class (AssetClass | None, optional): The asset class of the instrument. Defaults to None.
        id_notation (str | None, optional): The notation ID of the instrument. Defaults to None.
    Returns:
        httpx.Response: The HTTP response from the GET request.
    Raises:
        httpx.HTTPStatusError: If the HTTP request returned an unsuccessful status code.
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:

        url = compose_url(instrument_id, asset_class, id_notation)
        response = await client.get(url)
        response.raise_for_status()
        return response
