"""
Parser for the comdirect warrant detail page.

Extracts three groups of data from ``/inf/optionsscheine/detail/uebersicht/uebersicht.html``:

    market_data    — live bid/ask prices, spread, OHLC, timestamp, venue (Kursdaten)
    analytics      — Greeks and derived key metrics (Kennzahlen)
    reference_data — static instrument attributes (Stammdaten)

Functions:
    parse_warrant_detail: Resolve identifier, fetch detail page, parse and return all groups.
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup, Tag
from fastapi import HTTPException

from app.core.logging import logger
from app.models.instruments import AssetClass
from app.models.warrants import (
    WarrantAnalytics,
    WarrantDetailResponse,
    WarrantMarketData,
    WarrantReferenceData,
)
from app.parsers.instruments import parse_instrument_data
from app.scrapers.scrape_url import fetch_one

# ── Internal helpers ──────────────────────────────────────────────────────────


def _section_table(soup: BeautifulSoup, heading: str) -> Tag | None:
    """Return the first ``<table>`` inside the section with the given heading."""
    h2 = soup.find("h2", string=re.compile(heading))
    if not h2:
        return None
    return h2.parent.find("table")


def _td_text(table: Tag | None, label: str) -> str | None:
    """Find a ``<th>`` whose text contains *label* and return its sibling ``<td>`` text."""
    if table is None:
        return None
    for th in table.find_all("th"):
        if label in th.get_text(" ", strip=True):
            td = th.find_next_sibling("td")
            if td is None:
                td = th.parent.find("td")
            if td:
                return td.get_text(" ", strip=True).replace("\xa0", " ")
    return None


def _parse_float(text: str | None) -> float | None:
    """Parse a German-format number, ignoring trailing units / % signs.

    Examples: ``"0,75 %"`` → ``0.75``, ``"1.234,56 EUR"`` → ``1234.56``,
    ``"--"`` → ``None``.
    """
    if not text or text.strip() in ("", "--", "k. A."):
        return None
    first = text.strip().split()[0]
    try:
        return float(first.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _parse_amount_currency(text: str | None) -> tuple[float | None, str | None]:
    """Parse ``"225,29 USD"`` → ``(225.29, "USD")``.

    Returns ``(None, None)`` for missing / ``"--"`` values.
    """
    if not text or text.strip() in ("", "--", "k. A."):
        return None, None
    parts = text.strip().split()
    value: float | None = None
    currency: str | None = None
    if parts:
        try:
            value = float(parts[0].replace(".", "").replace(",", "."))
        except ValueError:
            pass
    if len(parts) >= 2:
        currency = parts[1]
    return value, currency


def _parse_date(text: str | None) -> date | None:
    """Parse ``DD.MM.YY`` or ``DD.MM.YYYY`` date strings."""
    if not text or text.strip() in ("", "--", "k. A."):
        return None
    stripped = text.strip()
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    return None


# ── Section parsers ───────────────────────────────────────────────────────────


def _parse_market_data(soup: BeautifulSoup) -> WarrantMarketData:
    table = _section_table(soup, "Kursdaten")

    # Bid and ask are wrapped in realtime spans (same as quote parser)
    bid: float | None = None
    ask: float | None = None
    if table:
        bid_th = table.find("th", string=re.compile(r"Geld"))
        if bid_th:
            span = bid_th.find_next("span", class_="realtime-indicator--value")
            bid = _parse_float(span.get_text(strip=True) if span else None)
            if bid is None:
                bid = _parse_float(_td_text(table, "Geld"))

        ask_th = table.find("th", string=re.compile(r"Brief"))
        if ask_th:
            span = ask_th.find_next("span", class_="realtime-indicator--value")
            ask = _parse_float(span.get_text(strip=True) if span else None)
            if ask is None:
                ask = _parse_float(_td_text(table, "Brief"))

    timestamp: datetime | None = None
    timestamp_str = _td_text(table, "Zeit")
    if timestamp_str:
        cleaned = re.sub(r"\s+", " ", timestamp_str).strip()
        for fmt in ("%d.%m.%y %H:%M", "%d.%m.%Y %H:%M"):
            try:
                timestamp = datetime.strptime(cleaned, fmt)
                break
            except ValueError:
                continue

    return WarrantMarketData(
        venue=_td_text(table, "Börse"),
        bid=bid,
        ask=ask,
        timestamp=timestamp,
        spread_percent=_parse_float(_td_text(table, "Spread")),
        spread_homogenized=_parse_float(_td_text(table, "Spread homogen")),
        prev_close=_parse_float(_td_text(table, "Vortag")),
        open=_parse_float(_td_text(table, "Eröffnung")),
        high=_parse_float(_td_text(table, "Hoch")),
        low=_parse_float(_td_text(table, "Tief")),
    )


def _parse_analytics(soup: BeautifulSoup) -> WarrantAnalytics:
    table = _section_table(soup, "Kennzahlen")

    break_even, break_even_currency = _parse_amount_currency(_td_text(table, "Break Even"))

    return WarrantAnalytics(
        delta=_parse_float(_td_text(table, "Delta")),
        leverage=_parse_float(_td_text(table, "Hebel")),
        omega=_parse_float(_td_text(table, "Omega")),
        implied_volatility=_parse_float(_td_text(table, "Implizite Volatilität")),
        premium_per_annum=_parse_float(_td_text(table, "Aufgeld p. a")),
        time_value=_parse_float(_td_text(table, "Zeitwert")),
        theta=_parse_float(_td_text(table, "Theta")),
        theoretical_value=_parse_float(_td_text(table, "Theoretischer Wert")),
        intrinsic_value=_parse_float(_td_text(table, "Innerer Wert")),
        break_even=break_even,
        break_even_currency=break_even_currency,
        moneyness=_parse_float(_td_text(table, "Moneyness")),
        premium=_parse_float(_td_text(table, "Aufgeld")),
        vega=_parse_float(_td_text(table, "Vega")),
        gamma=_parse_float(_td_text(table, "Gamma")),
    )


def _parse_action_flags(soup: BeautifulSoup) -> tuple[bool, bool]:
    """Detect ``issuer_action`` and ``issuer_no_fee_action`` from the detail page.

    Looks for the comdirect Aktion tooltip button near the warrant title:

    - ``issuer_action`` (off-market flat-fee): button ``<span class="button__inner">
      text equals ``"Aktion"``.
    - ``issuer_no_fee_action`` (on-exchange no-fee): the tooltip heading inside the
      same container contains ``"Börslich"`` (or the button text itself is ``"Börslich"``
      for warrants where only this flag is set).

    Args:
        soup: Parsed HTML of the warrant detail page.

    Returns:
        ``(issuer_action, issuer_no_fee_action)`` boolean tuple.
    """
    issuer_action = False
    issuer_no_fee_action = False

    aktion_btn = soup.find("button", attrs={"aria-label": re.compile(r"Aktion")})
    if not aktion_btn:
        return issuer_action, issuer_no_fee_action

    btn_text = aktion_btn.get_text(strip=True)
    if btn_text == "Aktion":
        issuer_action = True
    elif "rslich" in btn_text:  # Börslich
        issuer_no_fee_action = True

    # Check the tooltip heading inside the same container
    container = aktion_btn.find_parent("div", class_="layer-tooltip__container")
    if container:
        headline = container.find("div", class_=lambda c: c and "layer__header-headline" in c)
        if headline:
            heading = headline.get_text(strip=True)
            if "rslich" in heading:  # Börslich
                issuer_no_fee_action = True
            elif "Aktion" in heading:
                issuer_action = True

    return issuer_action, issuer_no_fee_action


def _parse_reference_data(soup: BeautifulSoup) -> WarrantReferenceData:
    table = _section_table(soup, "Stammdaten")

    strike, strike_currency = _parse_amount_currency(_td_text(table, "Basispreis"))
    underlying_price, underlying_price_currency = _parse_amount_currency(
        _td_text(table, "Kurs Basiswert")
    )

    issuer_action, issuer_no_fee_action = _parse_action_flags(soup)

    return WarrantReferenceData(
        isin=_td_text(table, "ISIN"),
        wkn=_td_text(table, "WKN"),
        last_trading_day=_parse_date(_td_text(table, "letzter Handelstag")),
        maturity_date=_parse_date(_td_text(table, "Fälligkeit")),
        strike=strike,
        strike_currency=strike_currency,
        underlying_name=_td_text(table, "Basiswert"),
        underlying_price=underlying_price,
        underlying_price_currency=underlying_price_currency,
        ratio=_td_text(table, "Bezugsverhältnis"),
        warrant_type=_td_text(table, "Typ"),
        issuer=_td_text(table, "Emittent"),
        currency=_td_text(table, "Währung"),
        symbol=_td_text(table, "Symbol"),
        issuer_action=issuer_action,
        issuer_no_fee_action=issuer_no_fee_action,
    )


# ── Public API ────────────────────────────────────────────────────────────────


async def parse_warrant_detail(identifier: str) -> WarrantDetailResponse:
    """Resolve *identifier* (WKN or ISIN), fetch the comdirect detail page, and parse it.

    Args:
        identifier: WKN or ISIN of the warrant (not the underlying).

    Returns:
        :class:`WarrantDetailResponse` with ``market_data``, ``analytics``,
        and ``reference_data`` sections.

    Raises:
        HTTPException 404: If the identifier cannot be resolved.
        HTTPException 400: If the resolved instrument is not a warrant.
    """
    logger.debug("parse_warrant_detail(%s)", identifier)
    instrument_data = await parse_instrument_data(identifier)

    if instrument_data.asset_class != AssetClass.WARRANT:
        raise HTTPException(
            status_code=400,
            detail=f"Instrument {identifier!r} is a {instrument_data.asset_class.value}, not a warrant",
        )

    id_notation = instrument_data.default_id_notation
    response = await fetch_one(str(instrument_data.wkn), AssetClass.WARRANT, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")

    isin = instrument_data.isin or ""
    wkn = str(instrument_data.wkn)

    result = WarrantDetailResponse(
        isin=isin,
        wkn=wkn,
        market_data=_parse_market_data(soup),
        analytics=_parse_analytics(soup),
        reference_data=_parse_reference_data(soup),
    )
    logger.debug("parse_warrant_detail(%s) done", identifier)
    return result
