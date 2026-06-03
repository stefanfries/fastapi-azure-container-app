"""
Parser for current market quote data.

Scrapes the comdirect instrument detail page to extract the current bid/ask
prices, spread, currency, timestamp, and trading venue for a given instrument.

Supported asset classes: STOCK, BOND, ETF, FONDS, WARRANT, CERTIFICATE.
Not supported: INDEX, COMMODITY, CURRENCY (not directly tradeable — no bid/ask).

comdirect uses two Kursdaten table layouts:
  - STOCK, WARRANT, BOND: bid/ask in ``<span class="realtime-indicator--value">``.
  - ETF: bid/ask in plain ``<td>`` cells; no "Börse" row; two "Zeit" rows.
  - FONDS: "Rücknahmepreis"/"Ausgabepreis" in plain ``<td>`` cells; no "Börse" row.
  - CERTIFICATE: bid/ask in realtime-indicator span when market open; ``--`` when closed.

Functions:
    _extract_table_price: Extract a numeric price from a Kursdaten table row.
    _extract_timestamp:   Extract the bid/ask timestamp from a Kursdaten table.
    parse_quote:          Fetch and parse the current market quote for an instrument.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup
from fastapi import HTTPException, status

from app.core.constants import special_asset_classes
from app.core.logging import logger
from app.models.quotes import Quote
from app.parsers.instruments import parse_instrument_data
from app.parsers.plugins.parsing_utils import extract_name_from_h1, extract_wkn_from_h2
from app.parsers.utils import check_valid_id_notation
from app.scrapers.scrape_url import fetch_one


def _extract_table_price(table: BeautifulSoup, label: str) -> float | None:
    """Extract a numeric price from a Kursdaten table row.

    Handles two comdirect HTML layouts:
      - Span layout (STOCK, WARRANT, BOND): value in ``<span class="realtime-indicator--value">``.
      - Plain layout (ETF, FONDS): value directly in the ``<td>`` cell.

    Returns None when the row is absent or the value is ``"--"``.
    """
    th = table.find("th", string=re.compile(rf"^{re.escape(label)}$"))
    if th is None:
        return None
    td = th.find_next("td")
    if td is None:
        return None
    span = td.find("span", class_="realtime-indicator--value")
    raw = span.text if span else td.text
    cleaned = re.sub(r"\s+", "", raw)  # remove all whitespace
    if not cleaned or cleaned.startswith("--"):
        return None
    try:
        return float(cleaned.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _extract_timestamp(table: BeautifulSoup) -> datetime | None:
    """Extract the bid/ask timestamp from a Kursdaten table.

    ETF/Fonds pages have two "Zeit" rows (one for the last price, one for bid/ask).
    When there is a "Brief" or "Ausgabepreis" row, the "Zeit" that follows it is
    the bid/ask timestamp.  For pages with a single "Zeit" row the first match is used.

    Returns None when no parseable timestamp is found (e.g. market is closed).
    """
    th_ask = table.find("th", string=re.compile(r"^Brief$|^Ausgabepreis$"))
    th_zeit = th_ask.find_next("th", string=re.compile(r"^Zeit$")) if th_ask is not None else None
    if th_zeit is None:
        th_zeit = table.find("th", string=re.compile(r"^Zeit$"))
    if th_zeit is None:
        return None
    raw = re.sub(r"\s+", " ", th_zeit.find_next("td").text).strip()
    if not raw or "--" in raw:
        return None
    try:
        return datetime.strptime(raw, "%d.%m.%y %H:%M")
    except ValueError:
        return None


async def parse_quote(instrument_id: str, id_notation: str | None) -> Quote:
    """Fetch and parse the current market quote for an instrument.

    Args:
        instrument_id: Instrument identifier (WKN, ISIN, or search term).
        id_notation: Optional specific trading venue notation.

    Returns:
        Quote with bid/ask prices, spread, currency, timestamp, and venue.

    Raises:
        HTTPException 501: For INDEX, COMMODITY, CURRENCY — not directly tradeable.
    """

    logger.debug("parse_quote(%s, id_notation=%s)", instrument_id, id_notation)
    instrument_data = await parse_instrument_data(instrument_id)

    if instrument_data.asset_class in special_asset_classes:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"Quote data for asset class {instrument_data.asset_class} is not supported: "
                "INDEX, COMMODITY, and CURRENCY are not directly tradeable and have no bid/ask prices."
            ),
        )

    match id_notation:
        case None:
            id_notation = instrument_data.default_id_notation
        case "preferred_id_notation_exchange_trading":
            id_notation = instrument_data.preferred_id_notation_exchange_trading
        case "preferred_id_notation_life_trading":
            id_notation = instrument_data.preferred_id_notation_life_trading
        case "default_id_notation":
            id_notation = instrument_data.default_id_notation
        case _:
            check_valid_id_notation(instrument_data, id_notation)

    # fetch instrument data from the web for the given id_notation
    try:
        response = await fetch_one(
            str(instrument_data.wkn), instrument_data.asset_class, id_notation
        )
    except Exception as exc:
        logger.warning("fetch_one failed for %s: %s", instrument_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach data source for {instrument_id}: {exc}",
        ) from exc
    soup = BeautifulSoup(response.content, "html.parser")

    # extract currency from soup object
    currency = soup.find_all("meta", itemprop="priceCurrency")[0]["content"]

    # extract name from soup object
    name = extract_name_from_h1(soup, remove_suffix=instrument_data.asset_class.comdirect_label)

    # extract WKN from soup object
    wkn_position = 2 if instrument_data.asset_class in special_asset_classes else 1
    wkn = extract_wkn_from_h2(soup, position_offset=wkn_position)

    # extract Table "Kursdaten" from soup object
    table = soup.find("h2", string=re.compile("Kursdaten")).parent.find("table")

    # Extract Bid — "Geld" for most asset classes; "Rücknahmepreis" for Fonds
    bid = _extract_table_price(table, "Geld")
    if bid is None:
        bid = _extract_table_price(table, "Rücknahmepreis")

    # Extract Ask — "Brief" for most asset classes; "Ausgabepreis" for Fonds
    ask = _extract_table_price(table, "Brief")
    if ask is None:
        ask = _extract_table_price(table, "Ausgabepreis")

    if bid is None or ask is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No current quote available for {instrument_id} — market may be closed.",
        )

    # Calculate spread as percentage of ask price (matching comdirect's formula)
    spread_percent = (ask - bid) / ask * 100 if ask > 0 else 0.0

    # Extract Timestamp
    timestamp = _extract_timestamp(table)
    if timestamp is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No current quote available for {instrument_id} — market may be closed.",
        )

    # Extract trading venue — not all asset classes have a "Börse" row in the Kursdaten table
    th_boerse = table.find("th", string="Börse")
    if th_boerse is not None:
        trading_venue = th_boerse.find_next("td").text.strip()
    else:
        # ETF and Fonds pages omit the Börse row; look up the venue by id_notation
        venue_maps = [
            m
            for m in (
                instrument_data.id_notations_life_trading,
                instrument_data.id_notations_exchange_trading,
            )
            if m
        ]
        trading_venue = next(
            (name for m in venue_maps for name, v in m.items() if v.id_notation == id_notation),
            id_notation or "",
        )

    quote = Quote(
        name=name,
        wkn=wkn,
        isin=instrument_data.isin,
        bid=bid,
        ask=ask,
        spread_percent=spread_percent,
        currency=currency,
        timestamp=timestamp,
        trading_venue=trading_venue,
        id_notation=id_notation,
    )
    logger.debug("parse_quote(%s) done", instrument_id)
    return quote
