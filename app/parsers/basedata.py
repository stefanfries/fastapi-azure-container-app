import re
import urllib.parse
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.constants import (
    asset_class_identifier_to_asset_class_map,
    special_asset_classes,
    standard_asset_classes,
)
from app.logging_config import logger
from app.models.basedata import AssetClass, BaseData, Isin, NotationType, Wkn
from app.scrapers.helper_functions import convert_to_int
from app.scrapers.scrape_url import fetch_one


def parse_asset_class(response: httpx.Response) -> AssetClass:
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


def parse_default_id_notation(response: httpx.Response) -> str | None:
    """
    Extracts the default ID notation from the given HTTP response.
    Args:
        response (httpx.Response): The HTTP response object from which to extract the default notation ID.
    Returns:
        str: The extracted default notation ID.
    """
    redirected_url = str(response.url)
    default_id_notation = urllib.parse.parse_qs(
        urllib.parse.urlparse(redirected_url).query
    ).get("ID_NOTATION", [None])[0]
    return default_id_notation


def parse_name(asset_class: AssetClass, soup: BeautifulSoup) -> str:
    """
    Extracts the name of the instrument from the given HTTP response.
    Args:
        response (httpx.Response): The HTTP response object from which to extract the name.
    Returns:
        str: The extracted name of the instrument.
    """

    headline_h1 = soup.select_one("h1")
    name = headline_h1.text.replace(f" {asset_class.value}", "").strip()
    return name


def parse_wkn(asset_class: AssetClass, soup: BeautifulSoup) -> Wkn:
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
        return Wkn(wkn=wkn)
    if asset_class in special_asset_classes:
        wkn = headline_h2.text.strip().split()[2]
        return Wkn(wkn=wkn)

    raise ValueError("Unsupported asset class")


def parse_isin(asset_class: AssetClass, soup: BeautifulSoup) -> str | None:
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
        return Isin(isin=isin)
    if asset_class in special_asset_classes:
        isin = None
        return Isin(isin=isin)
    logger.error("Unsupported asset class %s", asset_class)
    raise ValueError("Unsupported asset class")


def parse_symbol(asset_class: AssetClass, soup: BeautifulSoup) -> str | None:
    """
    Extracts the symbol from the given BeautifulSoup object based on the asset class.
    Args:
        asset_class (AssetClass): The class of the asset, which determines how the symbol is extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the symbol extracted.
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


def parse_id_notations(
    asset_class: AssetClass, soup: BeautifulSoup
) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
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
        return None, None

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
        # Originalzeile: name = table_rows[0].select("td")[1].text.strip()
        name = table_rows[0].select("td")[0].text.strip()
        notation_id = (
            table_rows[-1]
            .select_one("a")
            .attrs["data-plugin"]
            .split("ID_NOTATION%3D")[1]
            .split("%26")[0]
        )
        id_notations_dict[name] = notation_id

    # Extract Life Trading venues, add ID_Notation from Dictionary:
    lt_venues = soup.find_all("td", {"data-label": "LiveTrading"})
    lt_venue_dict = {}
    for v in lt_venues:
        venue = v.text.strip()
        if venue != "--":
            lt_venue_dict[venue] = id_notations_dict[venue]

    # Extract Exchange Trading venues, add ID_Notation from Dictionary:
    ex_venues = soup.find_all("td", {"data-label": "Börse"})
    ex_venue_dict = {}
    for v in ex_venues:
        venue = v.text.strip()
        if venue != "--":
            ex_venue_dict[venue] = id_notations_dict[venue]

    return lt_venue_dict, ex_venue_dict


def parse_venues(notation_type: NotationType, soup: BeautifulSoup) -> List[str]:
    """
    Extracts the venues from the given BeautifulSoup object based on the notation type.
    Args:
        notation_type (NotationType): The type of the notation, which determines how the venues are extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the venues are to be extracted.
    Returns:
        list[str]: The extracted venues.
    """
    venues = [
        venue.text.strip()
        for venue in soup.find_all("td", {"data-label": f"{notation_type.value}"})
        if venue.text.strip() != "--"
    ]
    return venues


def parse_price_fixings(notation_type: NotationType, soup: BeautifulSoup) -> List[int]:
    """
    Extracts the number of price fixings from the given BeautifulSoup object based on the notation type.
    Args:
        notation_type (NotationType): The type of the notation, which determines how the price fixings are extracted.
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML from which the price fixings are to be extracted.
    Returns:
        list[int]: The extracted number of price fixings.
    """
    data_label = (
        "Gestellte Kurse"
        if notation_type == NotationType.LIFE_TRADING
        else "Anzahl Kurse"
    )
    price_fixings_list = [
        convert_to_int(price_fixing.text.strip().replace(".", ""))
        for price_fixing in soup.find_all("td", {"data-label": f"{data_label}"})
        if price_fixing.text.strip() != "--"
    ]

    return price_fixings_list


def parse_preferred_notation_id_life_trading(
    asset_class: AssetClass, id_notations_dict: Dict[str, str], soup: BeautifulSoup
) -> str | None:

    if asset_class not in standard_asset_classes:
        return None

    # parse Life Trading venues:
    venues_list = parse_venues(NotationType.LIFE_TRADING, soup)

    # parse number of price fixings:
    price_fixings_list = parse_price_fixings(NotationType.LIFE_TRADING, soup)

    # create dictionary with venue as key and notation_id and price_fixings as values:
    venue_dict = {
        venue: {
            "notation_id": id_notations_dict[venue],
            "price_fixings": price_fixing,
        }
        for venue, price_fixing in zip(venues_list, price_fixings_list)
    }

    # select and return trading venue with highes number of price setting:
    if venue_dict:
        top_venue = max(venue_dict.values(), key=lambda v: int(v["price_fixings"]))
        notation_id = top_venue["notation_id"]
    else:
        notation_id = None

    return notation_id


def parse_preferred_notation_id_exchange_trading(
    asset_class: AssetClass, id_notations_dict: Dict[str, str], soup: BeautifulSoup
) -> str | None:

    if asset_class not in standard_asset_classes:
        return None

    # extract Exchange Trading venues:
    venues_list = parse_venues(NotationType.EXCH_TRADING, soup)

    # extract number of price fixings:
    price_fixings_list = parse_price_fixings(NotationType.EXCH_TRADING, soup)

    # create dictionary with venue as key and notation_id and price_fixings as values:
    venue_dict = {
        venue: {
            "notation_id": id_notations_dict[venue],
            "price_fixings": price_fixing,
        }
        for venue, price_fixing in zip(venues_list, price_fixings_list)
    }

    # select and return trading venue with highes number of price setting:
    if venue_dict:
        top_venue = max(venue_dict.values(), key=lambda v: int(v["price_fixings"]))
        notation_id = top_venue["notation_id"]
    else:
        notation_id = None

    return notation_id


async def parse_base_data(instrument: str) -> BaseData:
    """
    Fetches and parses the base data for a given instrument.
    Args:
        instrument_id (str): The ID of the instrument to fetch data for.
    Returns:
        BaseData: An object containing the base data of the instrument.
    Raises:
        HTTPException: If the request to fetch the instrument data fails.
        ValueError: If the instrument type or ID cannot be extracted from the response.
    """

    response = await fetch_one(instrument)
    soup = BeautifulSoup(response.content, "html.parser")
    asset_class = parse_asset_class(response)
    default_id_notation = parse_default_id_notation(response)
    name = parse_name(asset_class, soup)
    wkn = parse_wkn(asset_class, soup)
    isin = parse_isin(asset_class, soup)
    symbol = parse_symbol(asset_class, soup)
    id_notations_life_trading, id_notations_exchange_trading = parse_id_notations(
        asset_class, soup
    )
    preferred_id_notation_life_trading = parse_preferred_notation_id_life_trading(
        asset_class, id_notations_life_trading, soup
    )
    preferred_id_notation_exchange_trading = (
        parse_preferred_notation_id_exchange_trading(
            asset_class, id_notations_exchange_trading, soup
        )
    )
    base_data = BaseData(
        name=name,
        wkn=wkn,
        isin=isin,
        symbol=symbol,
        asset_class=asset_class,
        id_notations_life_trading=id_notations_life_trading,
        id_notations_exchange_trading=id_notations_exchange_trading,
        preferred_id_notation_life_trading=preferred_id_notation_life_trading,
        preferred_id_notation_exchange_trading=preferred_id_notation_exchange_trading,
        default_id_notation=default_id_notation,
    )
    return base_data


async def main():
    """
    Main function to parse and print the base data of a financial instrument.
    This function asynchronously retrieves the base data for a specified financial instrument
    using its instrument ID and prints the retrieved data.
    Args:
        None
    Returns:
        None
    """

    instrument_id = "DE000A0D9PT0"
    basedata = await parse_base_data(instrument_id)
    print(basedata)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
