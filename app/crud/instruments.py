import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.comdirect.de"
SEARCH_PATH = "/inf/search/all.html?SEARCH_VALUE="


async def get_page_from_url(url: str) -> httpx.Response:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        url = f"{BASE_URL}{SEARCH_PATH}{url}"
        print(f"fetching page from url: {url}")
        response = await client.get(url)
        response.raise_for_status()
        return response


def extract_instrument_type_from_response(response: httpx.Response) -> str:
    redirected_url = str(response.url)
    print(f"redirected_url: {redirected_url}, check instrument type")
    return redirected_url


def extract_soup_from_response(response: httpx.Response) -> BeautifulSoup:
    soup = BeautifulSoup(response.content, "html.parser")
    return soup


def extract_wkn_and_isin_from_spoup(soup: BeautifulSoup) -> tuple:
    headline_h2 = soup.select_one("h2")
    wkn = headline_h2.text.strip().split()[1]
    isin = headline_h2.text.strip().split()[3]
    return wkn, isin


async def main() -> None:
    """
    Main function to fetch and print page data from the web for a given query.
    This function asynchronously calls `get_page_data_from_web` with the query "Apple"
    and prints the result.
    Returns:
        None
    """
    search_phrase = "Apple"
    response = await get_page_from_url("search_phrase")
    redirected_url = extract_instrument_type_from_response(response)
    soup = extract_soup_from_response(response)
    wkn, isin = extract_wkn_and_isin_from_spoup(soup)

    print(f"redirected_url: {redirected_url}")
    print(f"Search phrase: {search_phrase}, WKN : {wkn}, ISIN: {isin}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
