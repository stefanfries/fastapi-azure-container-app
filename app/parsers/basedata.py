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
from app.models.basedata import AssetClass, BaseData, NotationType
from app.scrapers.helper_functions import convert_to_int
from app.scrapers.scrape_url import fetch_one


def valid_id_notation(basedata: BaseData, id_notation: str) -> bool:
    """
    Check if the given id_notation is valid within the provided BaseData instance.
    Args:
        basedata (BaseData): An instance of BaseData containing id notations.
        id_notation (str): The id notation to be validated.
    Returns:
        bool: True if the id_notation is found in either id_notations_life_trading or
              id_notations_exchange_trading of the basedata, False otherwise.
    """

    return (
        id_notation in basedata.id_notations_life_trading.values()
        or id_notation in basedata.id_notations_exchange_trading.values()
    )


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
    name = headline_h1.text.replace(f"{asset_class.value}", "").strip()
    return name


def parse_wkn(asset_class: AssetClass, soup: BeautifulSoup) -> str:
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
    logger.error("Unsupported asset class %s", asset_class)
    raise ValueError("Unsupported asset class")


def parse_isin(asset_class: AssetClass, soup: BeautifulSoup) -> str | None:
    """
    Extracts the ISIN from the given BeautifulSoup object.
    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML content.
    Returns:
        str: The ISIN as a string or None if not found.
    """

    headline_h2 = soup.select_one("h2")
    if asset_class in standard_asset_classes:
        if not headline_h2:
            logger.warning("H2 element not found for asset class %s", asset_class)
            return None
        h2_text = headline_h2.text.strip()
        logger.debug("H2 text for ISIN extraction: %s", h2_text)
        h2_parts = h2_text.split()
        logger.debug("H2 parts: %s", h2_parts)
        if len(h2_parts) > 3:
            isin = h2_parts[3]
            return isin
        else:
            logger.warning("Not enough parts in H2 text to extract ISIN: %s", h2_parts)
            return None
    if asset_class in special_asset_classes:
        return None
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
    Fetches and parses the base data for a given instrument using the plugin system.
    
    This function uses a plugin-based architecture where each asset class has its own
    parser implementation. This allows for flexible handling of different HTML structures
    across asset classes.
    
    Args:
        instrument: The ID of the instrument to fetch data for (WKN, ISIN, etc.)
        
    Returns:
        BaseData: An object containing the base data of the instrument.
        
    Raises:
        HTTPException: If the request to fetch the instrument data fails.
        ValueError: If the instrument type or ID cannot be extracted from the response,
                   or if no parser is available for the asset class.
    """
    from app.parsers.plugins.factory import ParserFactory
    
    # First fetch to determine asset class and get initial data
    response = await fetch_one(instrument)
    soup = BeautifulSoup(response.content, "html.parser")
    asset_class = parse_asset_class(response)
    
    # Get the appropriate parser for this asset class
    if not ParserFactory.is_registered(asset_class):
        # Fall back to legacy parsing for unregistered asset classes
        logger.warning(
            "No parser plugin registered for %s, falling back to legacy parsing",
            asset_class
        )
        return await _parse_base_data_legacy(instrument, response, soup, asset_class)
    
    parser = ParserFactory.get_parser(asset_class)
    
    # Get default ID_NOTATION from URL
    default_id_notation = parser.parse_default_id_notation_from_url(response)
    
    # Check if we need to refetch with ID_NOTATION
    if parser.needs_id_notation_refetch() and default_id_notation:
        logger.info(
            "Asset class %s requires refetch with ID_NOTATION %s",
            asset_class,
            default_id_notation
        )
        # Refetch with ID_NOTATION to get complete data
        response = await fetch_one(instrument, asset_class, default_id_notation)
        soup = BeautifulSoup(response.content, "html.parser")
    
    # Parse all fields using the plugin
    name = parser.parse_name(soup)
    wkn = parser.parse_wkn(soup)
    isin = parser.parse_isin(soup)
    symbol = parse_symbol(asset_class, soup)  # Still using legacy for symbol
    
    (
        id_notations_life_trading, 
        id_notations_exchange_trading,
        preferred_id_notation_life_trading,
        preferred_id_notation_exchange_trading
    ) = parser.parse_id_notations(soup, default_id_notation)
    
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


async def _parse_base_data_legacy(
    instrument: str, 
    response: httpx.Response, 
    soup: BeautifulSoup, 
    asset_class: AssetClass
) -> BaseData:
    """
    Legacy parsing function for asset classes without plugin support.
    
    This maintains backward compatibility for asset classes that haven't been
    migrated to the plugin system yet.
    """
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
