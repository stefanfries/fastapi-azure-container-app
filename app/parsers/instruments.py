"""
Parser for instrument master data.

Scrapes comdirect instrument detail pages to extract master data such as
name, WKN, ISIN, asset class, trading venue notations, and global identifiers.
Uses a plugin system for asset class-specific parsing.

Functions:
    valid_id_notation:        Check whether an id_notation is valid for an instrument.
    parse_asset_class:        Extract the asset class from an HTTP response.
    parse_default_id_notation: Extract the default id_notation from an HTTP response URL.
    parse_symbol:             Extract the ticker symbol from a parsed HTML page.
    parse_instrument_data:    Fetch and parse complete instrument master data (plugin-based).
"""

import re
import urllib.parse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.constants import asset_class_identifier_to_asset_class_map
from app.core.logging import logger
from app.models.instruments import AssetClass, Instrument
from app.scrapers.scrape_url import fetch_one
from app.services.identifier_enrichment import build_global_identifiers


def valid_id_notation(instrument_data: Instrument, id_notation: str) -> bool:
    """
    Check if the given id_notation is valid within the provided Instrument instance.
    Args:
        instrument_data (Instrument): An instance of Instrument containing id notations.
        id_notation (str): The id notation to be validated.
    Returns:
        bool: True if the id_notation is found in either id_notations_life_trading or
              id_notations_exchange_trading of the instrument_data, False otherwise.
    """

    return any(
        v.id_notation == id_notation for v in instrument_data.id_notations_life_trading.values()
    ) or any(
        v.id_notation == id_notation for v in instrument_data.id_notations_exchange_trading.values()
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
    default_id_notation = urllib.parse.parse_qs(urllib.parse.urlparse(redirected_url).query).get(
        "ID_NOTATION", [None]
    )[0]
    return default_id_notation


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


async def parse_instrument_data(instrument: str) -> Instrument:
    """
    Fetches and parses the instrument master data for a given instrument using the plugin system.

    Args:
        instrument: The ID of the instrument to fetch data for (WKN, ISIN, etc.)

    Returns:
        Instrument: An object containing the master data of the instrument.

    Raises:
        HTTPException: If the request to fetch the instrument data fails.
        ValueError: If the instrument type or ID cannot be extracted from the response.
    """
    from app.parsers.plugins.factory import ParserFactory

    response = await fetch_one(instrument)
    soup = BeautifulSoup(response.content, "html.parser")
    asset_class = parse_asset_class(response)

    parser = ParserFactory.get_parser(asset_class)

    default_id_notation = parse_default_id_notation(response)

    name = parser.parse_name(soup)
    wkn = parser.parse_wkn(soup)
    isin = parser.parse_isin(soup)
    symbol = parse_symbol(asset_class, soup)

    (
        id_notations_life_trading,
        id_notations_exchange_trading,
        preferred_id_notation_life_trading,
        preferred_id_notation_exchange_trading,
    ) = parser.parse_id_notations(soup, default_id_notation)

    global_identifiers = await build_global_identifiers(
        isin=isin,
        wkn=wkn,
        symbol_comdirect=symbol,
        asset_class=asset_class,
    )

    details = parser.parse_details(soup)

    instrument_data = Instrument(
        name=name,
        wkn=wkn,
        isin=isin,
        asset_class=asset_class,
        id_notations_life_trading=id_notations_life_trading,
        id_notations_exchange_trading=id_notations_exchange_trading,
        preferred_id_notation_life_trading=preferred_id_notation_life_trading,
        preferred_id_notation_exchange_trading=preferred_id_notation_exchange_trading,
        default_id_notation=default_id_notation,
        global_identifiers=global_identifiers,
        details=details,
    )
    return instrument_data
