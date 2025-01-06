from typing import Dict

import httpx

# from typing import AsyncGenerator, AsyncIterator, Dict, List

# these parameters are used to construct the URL for the request, should be moved to a config file
BASE_URL = "https://www.comdirect.de"
SEARCH_PATH = "/inf/search/all.html?"


async def fetch_one(instrument: str, query: Dict | None = None) -> httpx.Response:
    """
    Fetches a page for a given instrument from a remote server.
    Args:
        instrument (str): The identifier of the instrument to search for.
        query (dict | None): Optional. Additional query parameters to include in the request.
    Returns:
        httpx.Response: The HTTP response from the server containing the page data.
    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Base query parameters
        params = {"SEARCH_VALUE": instrument}
        if query:
            params.update(query)

        # Construct the request URL
        url = f"{BASE_URL}{SEARCH_PATH}"

        # Send the GET request
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response


"""
    async def fetch_many(
        urls: List[str], query: Dict | None = None
    ) -> AsyncIterator[httpx.Response]:
        '''
        Fetches multiple pages asynchronously.
        Args:
            urls (List[str]): A list of URLs to fetch.
            query (dict | None): Optional. Additional query parameters to include in the request.
        Returns:
            AsyncIterator[httpx.Response]: An iterator of HTTP responses.
        Raises:
            httpx.HTTPStatusError: If any response status code indicates an error.
        '''
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for url in urls:
                params = {}
                if query:
                    params.update(query)
                response = await client.get(url, params=params)
                response.raise_for_status()
                yield response
"""
