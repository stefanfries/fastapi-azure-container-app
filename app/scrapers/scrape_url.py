import httpx

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL, SEARCH_PATH
from app.models.basedata import AssetClass

# from typing import AsyncGenerator, AsyncIterator, Dict, List


async def fetch_base_one(instrument_id: str) -> httpx.Response:
    """
    Fetches data for a given instrument ID from a base URL.
    Args:
        instrument_id (str): The ID of the instrument to search for.
    Returns:
        httpx.Response: The HTTP response object containing the fetched data.
    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Base query parameters
        params = {"SEARCH_VALUE": instrument_id}

        # Construct the request URL
        url = f"{BASE_URL}{SEARCH_PATH}"

        # Send the GET request
        response = await client.get(url, params=params)
        response.raise_for_status()
        print(f"redirected URL: {response.url}")
        return response


async def fetch_details_one(
    instrument_id: str, asset_class: AssetClass, id_notation: str | None = None
) -> httpx.Response:
    """
    Fetch details for a given financial instrument.
    Args:
        instrument_id (str): The unique identifier for the financial instrument.
        asset_class (AssetClass): The asset class of the financial instrument.
        id_notation (str, optional): An optional notation ID for the instrument. Defaults to None.
    Returns:
        httpx.Response: The HTTP response object containing the details of the financial instrument.
    Raises:
        httpx.HTTPStatusError: If the HTTP request returned an unsuccessful status code.
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Base query parameters
        params = {"SEARCH_VALUE": instrument_id}
        if id_notation:
            params.update({"ID_NOTATION": id_notation})

        print(f"Params: {params}")

        # Construct the request URL
        path = ASSET_CLASS_DETAILS_PATH.get(asset_class, SEARCH_PATH)
        url = f"{BASE_URL}{path}"
        print(f"URL: {url}")

        # Send the GET request
        response = await client.get(url, params=params)
        response.raise_for_status()
        print(f"redirected URL: {response.url}")
        return response


"""
    async def base_fetch_many(
        urls: List[str], query: Dict | None = None
    ) -> AsyncIterator[httpx.Response]:
        Fetches multiple pages asynchronously.
        Args:
            urls (List[str]): A list of URLs to fetch.
            query (dict | None): Optional. Additional query parameters to include in the request.
        Returns:
            AsyncIterator[httpx.Response]: An iterator of HTTP responses.
        Raises:
            httpx.HTTPStatusError: If any response status code indicates an error.
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for url in urls:
                params = {}
                if query:
                    params.update(query)
                response = await client.get(url, params=params)
                response.raise_for_status()
                yield response
"""
