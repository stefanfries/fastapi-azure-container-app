import re
import urllib.parse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.logging_config import logger
from app.models.instruments import AssetClass, InstrumentBaseData

BASE_URL = "https://www.comdirect.de"
SEARCH_PATH = "/inf/search/all.html?"

standard_asset_classes = [
    AssetClass.STOCK,
    AssetClass.BOND,
    AssetClass.ETF,
    AssetClass.FONDS,
    AssetClass.WARRANT,
    AssetClass.CERTIFICATE,
]

special_asset_classes = [
    AssetClass.INDEX,
    AssetClass.COMMODITY,
    AssetClass.CURRENCY,
]

asset_classes = standard_asset_classes + special_asset_classes

asset_class_to_asset_class_identifier_map = {
    AssetClass.STOCK: "aktien",
    AssetClass.BOND: "anleihen",
    AssetClass.ETF: "etfs",
    AssetClass.FONDS: "fonds",
    AssetClass.WARRANT: "optionsscheine",
    AssetClass.CERTIFICATE: "zertifikate",
    AssetClass.INDEX: "indizes",
    AssetClass.COMMODITY: "rohstoffe",
    AssetClass.CURRENCY: "waehrungen",
}

asset_class_identifier_to_asset_class_map = {
    v: k for k, v in asset_class_to_asset_class_identifier_map.items()
}


async def get_page_for_instrument(instrument: str) -> httpx.Response:
    """
    Fetches a page for a given instrument from a remote server.
    Args:
        instrument (str): The identifier of the instrument to search for.
    Returns:
        httpx.Response: The HTTP response from the server containing the page data.
    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        params = {"SEARCH_VALUE": instrument}
        url = f"{BASE_URL}{SEARCH_PATH}"
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response


def scrape_asset_class_from_response(response: httpx.Response) -> AssetClass:
    """
    Extracts the asset class from the given HTTP response.
    Args:
        response (httpx.Response): The HTTP response object from which to extract the asset class.
    Returns:
        AssetClass | None: The extracted asset class if found.
    Raises:
        HTTPException: If the asset class is not found.
    """

    redirected_url = str(response.url)
    path = urllib.parse.urlparse(redirected_url).path
    asset_class_identifier = path.split("/")[2]
    if asset_class_identifier not in asset_class_identifier_to_asset_class_map:
        logger.error("Asset class not found %s", asset_class_identifier)
        logger.error("Redirected URL: %s", redirected_url)
        raise HTTPException(status_code=404, detail="Instrument not found")
    asset_class = asset_class_identifier_to_asset_class_map[asset_class_identifier]
    return asset_class


def scrape_name(asset_class: AssetClass, soup: BeautifulSoup) -> str:
    """
    Extracts the name of the instrument from the given HTTP response.
    Args:
        response (httpx.Response): The HTTP response object from which to extract the name.
    Returns:
        str: The extracted name of the instrument.
    """

    print(f"asset_class: {asset_class.value}")
    headline_h1 = soup.select_one("h1")
    name = headline_h1.text.replace(f" {asset_class.value}", "").strip()
    return name


def scrape_wkn(asset_class: AssetClass, soup: BeautifulSoup) -> str:
    """
    Extracts the WKN (Wertpapierkennnummer) from the given BeautifulSoup object based on the asset class.
    Args:
        asset_class (AssetClass): The class of the asset, which determines how the WKN is extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the WKN is to be extracted.
    Returns:
        str: The extracted WKN.
    Raises:
        ValueError: If the asset class is not supported.
    """

    headline_h2 = soup.select_one("h2")
    if asset_class in standard_asset_classes:
        wkn = headline_h2.text.strip().split()[1]
        return wkn
    if asset_class in special_asset_classes:
        wkn = headline_h2.text.strip().split()[2]
        return wkn
    raise ValueError("Unsupported asset class")


def scrape_isin(asset_class: AssetClass, soup: BeautifulSoup) -> str | None:
    """
    Extracts the ISIN from the given BeautifulSoup object.
    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML content.
    Returns:
        str: The ISIN as a string.
    """

    headline_h2 = soup.select_one("h2")
    if asset_class in standard_asset_classes:
        isin = headline_h2.text.strip().split()[3]
        return isin
    if asset_class in special_asset_classes:
        isin = None
        return isin
    logger.error("Unsupported asset class %s", asset_class)
    raise ValueError("Unsupported asset class")


def scrape_symbol(asset_class: AssetClass, soup: BeautifulSoup) -> str | None:
    """
    Extracts the symbol from the given BeautifulSoup object based on the asset class.
    Args:
        asset_class (AssetClass): The class of the asset, which determines how the symbol is extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the symbol is to be extracted.
    Returns:
        str: The extracted symbol.
    Raises:
        ValueError: If the asset class is not supported.
    """
    if asset_class == AssetClass.STOCK:
        row = soup.find(text=re.compile("Aktieninformationen")).parent.parent.find(
            "th", text=re.compile("Symbol")
        )
        symbol = None
        symbol_cell = None
        if row:
            symbol_cell = row.find_next_sibling("td")
        if symbol_cell:
            symbol = symbol_cell.text.strip()
        return symbol


def scrape_notation_ids(
    asset_class: AssetClass, soup: BeautifulSoup
) -> tuple[dict[str, str]] | None:
    """
    Extracts the notations from the given BeautifulSoup object based on the asset class.
    Args:
        asset_class (AssetClass): The class of the asset, which determines how the notations are extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the notations are to be extracted.
    Returns:
        list[str]: The extracted notations or None if notations not available.
    Raises:
        ValueError: If the asset class is not supported.
    """

    if asset_class not in standard_asset_classes:
        return None

    id_notations_dict = {}
    id_notations_list = soup.select("#marketSelect option")

    if len(id_notations_list) > 0:
        # multible trading venues available, therefore list of 'option's found
        for id_notation in id_notations_list:
            id_notations_dict[id_notation.attrs["label"]] = id_notation.attrs["value"]
    else:
        # only one trading venue, no selection option available, therefore no 'option's and no 'id_notation's found
        table_rows = soup.select("body div.grid.grid--no-gutter table.simple-table")[
            0
        ].select("tr")
        name = table_rows[0].select("td")[1].text.strip()
        iden = (
            table_rows[-1]
            .select_one("a")
            .attrs["data-plugin"]
            .split("ID_NOTATION%3D")[1]
            .split("%26")[0]
        )
        id_notations_dict[name] = iden
    # print(f"id_notations_dict: {id_notations_dict} \n\n")

    # Extrahieren aller Life Trading Handeslplätze und Ergänzung um ID_Notation aus Dictionary:
    lt_venues = soup.find_all("td", {"data-label": "LiveTrading"})
    lt_venue_dict = {}
    for v in lt_venues:
        venue = v.text.strip()
        if venue != "--":
            lt_venue_dict[venue] = id_notations_dict[venue]

    # Extrahieren aller Börsenhandeslplätze und Ergänzung um VenueID aus Dictionary:
    ex_venues = soup.find_all("td", {"data-label": "Börse"})
    ex_venue_dict = {}
    for v in ex_venues:
        venue = v.text.strip()
        if venue != "--":
            ex_venue_dict[venue] = id_notations_dict[venue]

    return lt_venue_dict, ex_venue_dict


async def scrape_instrument_base_data(instrument: str) -> InstrumentBaseData:
    """
    Fetches and parses the base data for a given instrument.
    Args:
        instrument_id (str): The ID of the instrument to fetch data for.
    Returns:
        InstrumentBaseData: An object containing the base data of the instrument.
    Raises:
        HTTPException: If the request to fetch the instrument data fails.
        ValueError: If the instrument type or ID cannot be extracted from the response.
    """

    response = await get_page_for_instrument(instrument)
    soup = BeautifulSoup(response.content, "html.parser")
    asset_class = scrape_asset_class_from_response(response)
    name = scrape_name(asset_class, soup)
    wkn = scrape_wkn(asset_class, soup)
    isin = scrape_isin(asset_class, soup)
    symbol = scrape_symbol(asset_class, soup)
    asset_class = scrape_asset_class_from_response(response)
    notation_ids_life_trading, notation_ids_exchange_trading = scrape_notation_ids(
        asset_class, soup
    )
    base_data = InstrumentBaseData(
        name=name,
        wkn=wkn,
        isin=isin,
        symbol=symbol,
        asset_class=asset_class,
        notation_ids_life_trading=notation_ids_life_trading,
        notation_ids_exchange_trading=notation_ids_exchange_trading,
    )

    return base_data


async def main():
    instrument_id = "DE000A0D9PT0"
    base_data = await scrape_instrument_base_data(instrument_id)
    print(base_data)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
