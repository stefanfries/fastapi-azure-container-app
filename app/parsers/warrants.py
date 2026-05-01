"""
Parser for the comdirect Optionsschein Finder (warrant screener).

Builds the warrant finder URL from structured parameters and resolves WKN/ISIN
identifiers for the underlying instrument via the existing instrument parser.

The actual HTML result parsing will be added in step 2 after analysing the
response structure of the trefferliste page.

Finder results URL base:
    https://www.comdirect.de/inf/optionsscheine/selector/trefferliste.html

    The UI entry point (finder.html) uses a hidden ``PRG_T`` parameter to
    redirect to the results page above.  We call trefferliste.html directly,
    dropping ``PRG_T``.

Functions:
    build_warrant_finder_url: Construct the trefferliste URL from resolved params.
    fetch_warrants:           Resolve underlying, build URL, fetch results, parse.

Greek / indicator filter parameters (not yet exposed in the API — reserved for step 2):
    Each of the 14 filters is controlled by a value + comparator pair.
    Comparator values: ``"gt"`` (greater than), ``"lt"`` (less than), ``"eq"`` (equal).
    When the value is empty the filter is disabled.

    ========================  ====================================================
    Parameter prefix          Description
    ========================  ====================================================
    IMPLIED_VOLATILITY        Implied volatility in percent
    DELTA                     Delta (- to +1, sensitivity to underlying movement)
    LEVERAGE                  Leverage ratio
    PREMIUM_PER_ANNUM         Time value cost per year in percent
    GEARING                   Omega / effective leverage
    PRESENT_VALUE             Present (theoretical) value
    SPREAD_ASK_PCT            Bid-ask spread as a percentage of ask price
    THETA_DAY                 Theta per calendar day (time decay)
    THEORETICAL_VALUE         Theoretical fair value
    INTRINSIC_VALUE           Intrinsic value
    BREAK_EVEN                Break-even price of the underlying
    MONEYNESS                 Moneyness in percent
    VEGA                      Vega (sensitivity to implied volatility change)
    GAMMA                     Gamma (rate of change of delta)
    ========================  ====================================================

    URL naming convention: each prefix becomes two query parameters, e.g.
        ``DELTA_VALUE=0.5&DELTA_COMPARATOR=gt``
"""

import asyncio
from datetime import date, datetime
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup, Tag
from fastapi import HTTPException

from app.core.constants import BASE_URL
from app.core.logging import logger
from app.models.warrants import (
    Warrant,
    WarrantFinderResponse,
    WarrantMaturityRange,
    WarrantPreselection,
)
from app.parsers.instruments import parse_instrument_data

WARRANT_FINDER_RESULTS_URL = f"{BASE_URL}/inf/optionsscheine/selector/trefferliste.html"

# Greek/indicator filter parameter prefixes in the order comdirect expects them.
_GREEK_PREFIXES: tuple[str, ...] = (
    "IMPLIED_VOLATILITY",
    "DELTA",
    "LEVERAGE",
    "PREMIUM_PER_ANNUM",
    "GEARING",
    "PRESENT_VALUE",
    "SPREAD_ASK_PCT",
    "THETA_DAY",
    "THEORETICAL_VALUE",
    "INTRINSIC_VALUE",
    "BREAK_EVEN",
    "MONEYNESS",
    "VEGA",
    "GAMMA",
)


def _greek_filter_pairs(
    prefix: str,
    min_val: float | None,
    max_val: float | None,
) -> list[tuple[str, str]]:
    """Build ``(VALUE, COMPARATOR)`` tuple pairs for one Greek filter.

    Comdirect supports a lower bound, an upper bound, or both for the same
    Greek by repeating the parameter name in the query string::

        DELTA_VALUE=0.5&DELTA_COMPARATOR=gt&DELTA_VALUE=0.8&DELTA_COMPARATOR=lt

    When neither bound is provided the filter is emitted as disabled
    (empty value, comparator ``gt``).

    Args:
        prefix:  Comdirect parameter prefix, e.g. ``"DELTA"``.
        min_val: Lower bound (``> min_val``), or ``None`` to skip.
        max_val: Upper bound (``< max_val``), or ``None`` to skip.

    Returns:
        List of ``(key, value)`` tuples ready for :func:`urllib.parse.urlencode`.
    """
    pairs: list[tuple[str, str]] = []
    if min_val is not None:
        pairs += [(f"{prefix}_VALUE", str(min_val)), (f"{prefix}_COMPARATOR", "gt")]
    if max_val is not None:
        pairs += [(f"{prefix}_VALUE", str(max_val)), (f"{prefix}_COMPARATOR", "lt")]
    if not pairs:
        pairs = [(f"{prefix}_VALUE", ""), (f"{prefix}_COMPARATOR", "gt")]
    return pairs


def _parse_maturity_param(value: str | None) -> tuple[str, str, bool]:
    """Parse a maturity date input into a ``(range_value, calendar_value, use_date_picker)`` tuple.

    When an explicit date is supplied comdirect also requires a companion
    checkbox parameter ``date-DATE_TIME_MATURITY_*_CAL=on`` to activate the
    date picker widget.  The third tuple element signals whether this
    checkbox should be emitted.

    Accepts:
        - ``None``             → ``("", "", False)``                           — filter disabled
        - ``"Range_NOW"`` etc. → ``(value, "", False)``                        — pass through as-is
        - ``"YYYY-MM-DD"``     → ``("Range_CHOOSE_DATE", "DD.MM.YYYY", True)`` — ISO date string
        - ``"DD.MM.YYYY"``     → ``("Range_CHOOSE_DATE", value, True)``        — comdirect date format

    Args:
        value: Raw maturity input from the API caller, or ``None``.

    Returns:
        Tuple of (comdirect ``DATE_TIME_MATURITY_*`` value,
                  comdirect ``DATE_TIME_MATURITY_*_CAL`` value,
                  whether to emit ``date-DATE_TIME_MATURITY_*_CAL=on``).

    Raises:
        ValueError: If *value* is not a recognised range code or a parseable date string.
    """
    if value is None:
        return ("", "", False)

    if value.startswith("Range_"):
        return (value, "", False)

    # ISO date: YYYY-MM-DD
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return ("Range_CHOOSE_DATE", dt.strftime("%d.%m.%Y"), True)
    except ValueError:
        pass

    # Already in comdirect calendar format: DD.MM.YYYY
    try:
        datetime.strptime(value, "%d.%m.%Y")
        return ("Range_CHOOSE_DATE", value, True)
    except ValueError:
        pass

    raise ValueError(
        f"Invalid maturity date: {value!r}. "
        "Use a Range_* code (e.g. 'Range_6M') or a date in YYYY-MM-DD or DD.MM.YYYY format."
    )


def build_warrant_finder_url(
    id_notation_underlying: str,
    underlying_name: str,
    preselection: WarrantPreselection = WarrantPreselection.ALL,
    issuer_action: bool = False,
    issuer_no_fee_action: bool = False,
    strike_min: float | None = None,
    strike_max: float | None = None,
    maturity_from: str | None = None,
    maturity_to: str | None = None,
    issuer_group_id: str | None = None,
    # Greek / indicator filters — each supports an optional lower and upper bound.
    # Comdirect encodes dual bounds as repeated query parameters (Strategy C).
    delta_min: float | None = None,
    delta_max: float | None = None,
    omega_min: float | None = None,
    omega_max: float | None = None,
    moneyness_min: float | None = None,
    moneyness_max: float | None = None,
    premium_per_annum_max: float | None = None,
    implied_volatility_min: float | None = None,
    implied_volatility_max: float | None = None,
    leverage_min: float | None = None,
    leverage_max: float | None = None,
    premium_per_annum_min: float | None = None,
    spread_ask_pct_min: float | None = None,
    spread_ask_pct_max: float | None = None,
    theta_day_min: float | None = None,
    theta_day_max: float | None = None,
    present_value_min: float | None = None,
    present_value_max: float | None = None,
    theoretical_value_min: float | None = None,
    theoretical_value_max: float | None = None,
    intrinsic_value_min: float | None = None,
    intrinsic_value_max: float | None = None,
    break_even_min: float | None = None,
    break_even_max: float | None = None,
    vega_min: float | None = None,
    vega_max: float | None = None,
    gamma_min: float | None = None,
    gamma_max: float | None = None,
) -> str:
    """Build the comdirect warrant finder results URL from resolved parameters.

    All 14 Greek/indicator filter parameter pairs are always included.  When
    bounds are provided they are encoded as repeated query parameters so that
    comdirect applies both a lower and an upper bound for the same Greek.

    Args:
        id_notation_underlying:  comdirect ``id_notation`` of the underlying instrument,
                                 obtained via :func:`parse_instrument_data`.
        underlying_name:         Human-readable name of the underlying
                                 (e.g. ``"NVIDIA CORPORATION"``).
        preselection:            Warrant type filter: CALL, PUT, OTHER, or ALL.
                                 Defaults to ``ALL``.
        issuer_action:           Include off-market flat-fee (Aktion) warrants.
                                 Maps to ``ISSUER_ACTION``.  Defaults to ``False``.
        issuer_no_fee_action:    Include market no-fee warrants.
                                 Maps to ``ISSUER_NO_FEE_ACTION``.  Defaults to ``False``.
        strike_min:              Minimum strike price (``STRIKE_ABS_FROM``).
        strike_max:              Maximum strike price (``STRIKE_ABS_TO``).
        maturity_from:           Start of maturity range — Range_* code or date string.
        maturity_to:             End of maturity range  — Range_* code or date string.
        issuer_group_id:         Comdirect issuer group ID (``ID_GROUP_ISSUER``).
        delta_min:               Lower bound for Delta (``DELTA > delta_min``).
        delta_max:               Upper bound for Delta (``DELTA < delta_max``).
        omega_min:               Lower bound for Omega/effective leverage (``GEARING > omega_min``).
        omega_max:               Upper bound for Omega/effective leverage (``GEARING < omega_max``).
        moneyness_min:           Lower bound for Moneyness in % (``MONEYNESS > moneyness_min``).
        moneyness_max:           Upper bound for Moneyness in % (``MONEYNESS < moneyness_max``).
        premium_per_annum_max:   Upper bound for Premium p.a. in % (``PREMIUM_PER_ANNUM < premium_per_annum_max``).
        implied_volatility_min:  Lower bound for implied volatility in % (``IMPLIED_VOLATILITY > implied_volatility_min``).
        implied_volatility_max:  Upper bound for implied volatility in % (``IMPLIED_VOLATILITY < implied_volatility_max``).
        leverage_min:            Lower bound for Leverage (``LEVERAGE > leverage_min``).
        leverage_max:            Upper bound for Leverage (``LEVERAGE < leverage_max``).
        premium_per_annum_min:   Lower bound for Premium p.a. in % (``PREMIUM_PER_ANNUM > premium_per_annum_min``).
        spread_ask_pct_min:      Lower bound for Spread/Ask % (``SPREAD_ASK_PCT > spread_ask_pct_min``).
        spread_ask_pct_max:      Upper bound for Spread/Ask % (``SPREAD_ASK_PCT < spread_ask_pct_max``).
        theta_day_min:           Lower bound for Theta/day (``THETA_DAY > theta_day_min``).
        theta_day_max:           Upper bound for Theta/day (``THETA_DAY < theta_day_max``).
        present_value_min:       Lower bound for Present Value (``PRESENT_VALUE > present_value_min``).
        present_value_max:       Upper bound for Present Value (``PRESENT_VALUE < present_value_max``).
        theoretical_value_min:   Lower bound for Theoretical Value (``THEORETICAL_VALUE > theoretical_value_min``).
        theoretical_value_max:   Upper bound for Theoretical Value (``THEORETICAL_VALUE < theoretical_value_max``).
        intrinsic_value_min:     Lower bound for Intrinsic Value (``INTRINSIC_VALUE > intrinsic_value_min``).
        intrinsic_value_max:     Upper bound for Intrinsic Value (``INTRINSIC_VALUE < intrinsic_value_max``).
        break_even_min:          Lower bound for Break Even (``BREAK_EVEN > break_even_min``).
        break_even_max:          Upper bound for Break Even (``BREAK_EVEN < break_even_max``).
        vega_min:                Lower bound for Vega (``VEGA > vega_min``).
        vega_max:                Upper bound for Vega (``VEGA < vega_max``).
        gamma_min:               Lower bound for Gamma (``GAMMA > gamma_min``).
        gamma_max:               Upper bound for Gamma (``GAMMA < gamma_max``).

    Returns:
        Fully qualified URL for the comdirect warrant finder results page.
    """
    maturity_from_range, maturity_from_cal, from_is_date = _parse_maturity_param(maturity_from)
    maturity_to_range, maturity_to_cal, to_is_date = _parse_maturity_param(maturity_to)

    # Use a list of tuples (not a dict) so that repeated Greek filter keys are
    # preserved when both a lower and upper bound are set for the same Greek.
    params: list[tuple[str, str]] = [
        ("FORM_NAME", "DerivativesSelectorOptionsscheineForm"),
        ("PRESELECTION", preselection.value),
        ("ISSUER_ACTION", str(issuer_action).lower()),
        ("ISSUER_NO_FEE_ACTION", str(issuer_no_fee_action).lower()),
        ("ID_NOTATION_UNDERLYING", id_notation_underlying),
        ("UNDERLYING_TYPE", "FREI"),
        ("UNDERLYING_NAME_SEARCH", underlying_name),
        ("PREDEFINED_UNDERLYING", ""),
        (
            "STRIKE_ABS_FROM",
            (str(int(strike_min)) if strike_min == int(strike_min) else str(strike_min))
            if strike_min is not None
            else "",
        ),
        (
            "STRIKE_ABS_TO",
            (str(int(strike_max)) if strike_max == int(strike_max) else str(strike_max))
            if strike_max is not None
            else "",
        ),
        ("DATE_TIME_MATURITY_FROM", maturity_from_range),
        ("DATE_TIME_MATURITY_FROM_CAL", maturity_from_cal),
    ]
    if from_is_date:
        params.append(("date-DATE_TIME_MATURITY_FROM_CAL", "on"))
    params += [
        ("DATE_TIME_MATURITY_TO", maturity_to_range),
        ("DATE_TIME_MATURITY_TO_CAL", maturity_to_cal),
    ]
    if to_is_date:
        params.append(("date-DATE_TIME_MATURITY_TO_CAL", "on"))
    params.append(("ID_GROUP_ISSUER", issuer_group_id or ""))

    # Greek / indicator filters — in comdirect's expected order.
    # Exposed filters use caller-supplied bounds; unexposed ones are emitted disabled.
    params += _greek_filter_pairs("IMPLIED_VOLATILITY", implied_volatility_min, implied_volatility_max)
    params += _greek_filter_pairs("DELTA", delta_min, delta_max)
    params += _greek_filter_pairs("LEVERAGE", leverage_min, leverage_max)
    params += _greek_filter_pairs("PREMIUM_PER_ANNUM", premium_per_annum_min, premium_per_annum_max)
    params += _greek_filter_pairs("GEARING", omega_min, omega_max)
    params += _greek_filter_pairs("PRESENT_VALUE", present_value_min, present_value_max)
    params += _greek_filter_pairs("SPREAD_ASK_PCT", spread_ask_pct_min, spread_ask_pct_max)
    params += _greek_filter_pairs("THETA_DAY", theta_day_min, theta_day_max)
    params += _greek_filter_pairs("THEORETICAL_VALUE", theoretical_value_min, theoretical_value_max)
    params += _greek_filter_pairs("INTRINSIC_VALUE", intrinsic_value_min, intrinsic_value_max)
    params += _greek_filter_pairs("BREAK_EVEN", break_even_min, break_even_max)
    params += _greek_filter_pairs("MONEYNESS", moneyness_min, moneyness_max)
    params += _greek_filter_pairs("VEGA", vega_min, vega_max)
    params += _greek_filter_pairs("GAMMA", gamma_min, gamma_max)
    params.append(("keepCookie", "true"))

    return f"{WARRANT_FINDER_RESULTS_URL}?{urlencode(params)}"


def _get_total_pages(soup: BeautifulSoup) -> int:
    """Return the total number of result pages from the pagination widget.

    Counts ``<span class="pagination__page">`` elements that contain an ``<a>``
    (i.e. are navigable pages, not the active page).  Returns 1 when no
    pagination widget is found.

    Args:
        soup: Parsed HTML of the warrant finder results page.

    Returns:
        Total page count (>= 1).
    """
    pager = soup.find("div", class_="pagination")
    if not pager:
        return 1
    page_numbers = [
        int(span.get_text(strip=True))
        for span in pager.find_all("span", class_="pagination__page")
        if span.get_text(strip=True).isdigit()
    ]
    return max(page_numbers) if page_numbers else 1


def _parse_date(value: str) -> date | None:
    """Parse a comdirect date string (``DD.MM.YY``) to a :class:`date`.

    Returns ``None`` for ``"--"`` or any unparseable value.

    Args:
        value: Date string, e.g. ``"18.12.26"``.

    Returns:
        Parsed :class:`date` or ``None``.
    """
    value = value.strip()
    if not value or value == "--":
        return None
    try:
        return datetime.strptime(value, "%d.%m.%y").date()
    except ValueError:
        return None


def _cell(row: Tag, label: str) -> Tag | None:
    """Return the first ``<td>`` or ``<th>`` whose ``data-label`` matches *label*.

    Args:
        row:   A ``<tr>`` BeautifulSoup Tag.
        label: The ``data-label`` attribute value to search for.

    Returns:
        Matching cell Tag, or ``None`` if not found.
    """
    return row.find(["td", "th"], attrs={"data-label": label})


def _parse_warrant_rows(soup: BeautifulSoup) -> list[Warrant]:
    """Extract all warrant rows from a single finder results page.

    Sponsored / ad rows (those with a ``colspan`` attribute on any ``<td>``)
    are silently skipped.  Rows with fewer than 8 individual cells are also
    skipped.

    Cell values are located by ``data-label`` attribute so the result is
    independent of column order:

    ========================  ====================================================
    data-label                Extracted field
    ========================  ====================================================
    ``"ISIN"``                ``isin``
    ``"WKN"``                 ``wkn``
    ``"ISINWKN"``             ``link`` (first ``<a>`` href, prepended with BASE_URL)
    ``"Basispreis"``          ``strike`` and ``strike_currency``
    ``"Bez.Verh."``           ``ratio`` (stored as-is, e.g. ``"10 : 1"``)
    ``"Fälligkeit"``          ``maturity_date``
    ``"letzter H.Tag"``       ``last_trading_day``
    ``"Emittent"``            ``issuer``
    ========================  ====================================================

    Args:
        soup: Parsed HTML of one warrant finder results page.

    Returns:
        List of :class:`Warrant` objects parsed from this page.
    """
    table = soup.find("table", class_="table--comparison")
    if not table:
        return []

    warrants: list[Warrant] = []
    for row in table.find_all("tr"):
        # A valid warrant row must have a cell with data-label="ISIN"
        isin_cell = _cell(row, "ISIN")
        if not isin_cell:
            continue

        isin = isin_cell.get_text(strip=True)
        if not isin:
            continue

        wkn_cell = _cell(row, "WKN")
        isinwkn_cell = _cell(row, "ISINWKN")
        strike_cell = _cell(row, "Basispreis")
        ratio_cell = _cell(row, "Bez.Verh.")
        maturity_cell = _cell(row, "Fälligkeit")
        last_day_cell = _cell(row, "letzter H.Tag")
        issuer_cell = _cell(row, "Emittent")

        # WKN: prefer dedicated cell, fall back to "--" (e.g. NL/CH issuers)
        wkn = wkn_cell.get_text(strip=True) if wkn_cell else "--"

        # Link from the ISINWKN desktop cell
        link = ""
        if isinwkn_cell:
            a = isinwkn_cell.find("a", href=True)
            if a:
                href = a["href"]
                link = href if href.startswith("http") else f"{BASE_URL}{href}"

        # Strike: "110,00 USD" → (110.0, "USD")
        strike: float | None = None
        strike_currency: str | None = None
        if strike_cell:
            raw = strike_cell.get_text(" ", strip=True).replace("\xa0", " ")
            parts = raw.split()
            if parts and parts[0] != "--":
                try:
                    strike = float(parts[0].replace(".", "").replace(",", "."))
                    if len(parts) >= 2:
                        strike_currency = parts[1]
                except ValueError:
                    pass

        # Ratio: "10 : 1" → stored as-is
        ratio: str | None = None
        if ratio_cell:
            raw_ratio = ratio_cell.get_text(" ", strip=True).replace("\xa0", " ").strip()
            if raw_ratio and raw_ratio != "--":
                ratio = raw_ratio

        maturity_date = _parse_date(maturity_cell.get_text(strip=True)) if maturity_cell else None
        last_trading_day = (
            _parse_date(last_day_cell.get_text(strip=True)) if last_day_cell else None
        )
        issuer = issuer_cell.get_text(strip=True) if issuer_cell else None
        if issuer == "--":
            issuer = None

        warrants.append(
            Warrant(
                isin=isin,
                wkn=wkn,
                link=link,
                strike=strike,
                strike_currency=strike_currency,
                ratio=ratio,
                maturity_date=maturity_date,
                last_trading_day=last_trading_day,
                issuer=issuer,
            )
        )

    return warrants


async def fetch_warrants(
    underlying: str,
    preselection: WarrantPreselection = WarrantPreselection.ALL,
    issuer_action: bool = False,
    issuer_no_fee_action: bool = False,
    strike_min: float | None = None,
    strike_max: float | None = None,
    maturity_from: str | None = None,
    maturity_to: str | None = None,
    issuer_group_id: str | None = None,
    delta_min: float | None = None,
    delta_max: float | None = None,
    omega_min: float | None = None,
    omega_max: float | None = None,
    moneyness_min: float | None = None,
    moneyness_max: float | None = None,
    premium_per_annum_max: float | None = None,
    implied_volatility_min: float | None = None,
    implied_volatility_max: float | None = None,
    leverage_min: float | None = None,
    leverage_max: float | None = None,
    premium_per_annum_min: float | None = None,
    spread_ask_pct_min: float | None = None,
    spread_ask_pct_max: float | None = None,
    theta_day_min: float | None = None,
    theta_day_max: float | None = None,
    present_value_min: float | None = None,
    present_value_max: float | None = None,
    theoretical_value_min: float | None = None,
    theoretical_value_max: float | None = None,
    intrinsic_value_min: float | None = None,
    intrinsic_value_max: float | None = None,
    break_even_min: float | None = None,
    break_even_max: float | None = None,
    vega_min: float | None = None,
    vega_max: float | None = None,
    gamma_min: float | None = None,
    gamma_max: float | None = None,
) -> WarrantFinderResponse:
    """Resolve the underlying, build the finder URL, fetch results, and parse.

    Args:
        underlying:              WKN or ISIN of the underlying instrument.
        preselection:            Warrant type filter.  Defaults to ``ALL``.
        issuer_action:           Include off-market flat-fee (Aktion) warrants.
        issuer_no_fee_action:    Include market no-fee warrants.
        strike_min:              Minimum strike price.
        strike_max:              Maximum strike price.
        maturity_from:           Start of maturity range (Range_* code or date string).
                                 Defaults to ``Range_NOW``.
        maturity_to:             End of maturity range (Range_* code or date string).
        issuer_group_id:         Comdirect issuer group ID (``ID_GROUP_ISSUER``).
        delta_min:               Lower bound for Delta.
        delta_max:               Upper bound for Delta.
        omega_min:               Lower bound for Omega (effective leverage / GEARING).
        omega_max:               Upper bound for Omega (effective leverage / GEARING).
        moneyness_min:           Lower bound for Moneyness in %.
        moneyness_max:           Upper bound for Moneyness in %.
        premium_per_annum_max:   Upper bound for Premium p.a. in %.
        implied_volatility_min:  Lower bound for implied volatility in %.
        implied_volatility_max:  Upper bound for implied volatility in %.        leverage_min:             Lower bound for Leverage.
        leverage_max:             Upper bound for Leverage.
        premium_per_annum_min:    Lower bound for Premium p.a. in %.
        spread_ask_pct_min:       Lower bound for Spread/Ask %.
        spread_ask_pct_max:       Upper bound for Spread/Ask %.
        theta_day_min:            Lower bound for Theta/day.
        theta_day_max:            Upper bound for Theta/day.
        present_value_min:        Lower bound for Present Value.
        present_value_max:        Upper bound for Present Value.
        theoretical_value_min:    Lower bound for Theoretical Value.
        theoretical_value_max:    Upper bound for Theoretical Value.
        intrinsic_value_min:      Lower bound for Intrinsic Value.
        intrinsic_value_max:      Upper bound for Intrinsic Value.
        break_even_min:           Lower bound for Break Even.
        break_even_max:           Upper bound for Break Even.
        vega_min:                 Lower bound for Vega.
        vega_max:                 Upper bound for Vega.
        gamma_min:                Lower bound for Gamma.
        gamma_max:                Upper bound for Gamma.
    Returns:
        :class:`WarrantFinderResponse` with the constructed URL, result count,
        and the list of parsed :class:`Warrant` objects.

    Raises:
        HTTPException 404: If the underlying identifier cannot be resolved.
        HTTPException 502: If the comdirect finder request fails or the
                           underlying has no ``default_id_notation``.
    """
    # Step 1: resolve WKN/ISIN → id_notation + name via instrument parser
    logger.info("Resolving underlying '%s' to id_notation", underlying)
    try:
        instrument_data = await parse_instrument_data(underlying)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve underlying '%s': %s", underlying, exc)
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve underlying '{underlying}'",
        ) from exc

    id_notation = instrument_data.default_id_notation
    if not id_notation:
        raise HTTPException(
            status_code=502,
            detail=f"Could not determine id_notation for underlying '{underlying}'",
        )

    underlying_name = instrument_data.name
    logger.info(
        "Underlying '%s' resolved: id_notation=%s, name='%s'",
        underlying,
        id_notation,
        underlying_name,
    )

    # Step 2: build the finder URL
    url = build_warrant_finder_url(
        id_notation_underlying=id_notation,
        underlying_name=underlying_name,
        preselection=preselection,
        issuer_action=issuer_action,
        issuer_no_fee_action=issuer_no_fee_action,
        strike_min=strike_min,
        strike_max=strike_max,
        maturity_from=maturity_from or WarrantMaturityRange.NOW.value,
        maturity_to=maturity_to,
        issuer_group_id=issuer_group_id,
        delta_min=delta_min,
        delta_max=delta_max,
        omega_min=omega_min,
        omega_max=omega_max,
        moneyness_min=moneyness_min,
        moneyness_max=moneyness_max,
        premium_per_annum_max=premium_per_annum_max,
        implied_volatility_min=implied_volatility_min,
        implied_volatility_max=implied_volatility_max,
        leverage_min=leverage_min,
        leverage_max=leverage_max,
        premium_per_annum_min=premium_per_annum_min,
        spread_ask_pct_min=spread_ask_pct_min,
        spread_ask_pct_max=spread_ask_pct_max,
        theta_day_min=theta_day_min,
        theta_day_max=theta_day_max,
        present_value_min=present_value_min,
        present_value_max=present_value_max,
        theoretical_value_min=theoretical_value_min,
        theoretical_value_max=theoretical_value_max,
        intrinsic_value_min=intrinsic_value_min,
        intrinsic_value_max=intrinsic_value_max,
        break_even_min=break_even_min,
        break_even_max=break_even_max,
        vega_min=vega_min,
        vega_max=vega_max,
        gamma_min=gamma_min,
        gamma_max=gamma_max,
    )
    logger.info("Warrant finder URL: %s", url)

    # Step 3: fetch page 1, read total page count, then fetch remaining pages
    # with a semaphore to avoid overwhelming comdirect with too many concurrent
    # connections (which causes ConnectError / rate-limiting).
    _MAX_CONCURRENT_PAGES = 5

    results: list[Warrant] = []
    pages_fetched = 0
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

            first_soup = BeautifulSoup(response.content, "html.parser")
            total_pages = _get_total_pages(first_soup)
            logger.info("Warrant finder has %d page(s)", total_pages)

            results = _parse_warrant_rows(first_soup)
            pages_fetched = 1

            if total_pages > 1:
                semaphore = asyncio.Semaphore(_MAX_CONCURRENT_PAGES)

                async def _fetch_page(offset: int) -> list[Warrant]:
                    async with semaphore:
                        page_response = await client.get(f"{url}&OFFSET={offset}")
                        page_response.raise_for_status()
                        return _parse_warrant_rows(
                            BeautifulSoup(page_response.content, "html.parser")
                        )

                page_results = await asyncio.gather(
                    *[_fetch_page(i) for i in range(1, total_pages)]
                )
                for page_warrants in page_results:
                    results.extend(page_warrants)
                pages_fetched = total_pages

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("Warrant finder request failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Warrant finder request failed",
        ) from exc

    # comdirect renders each row twice (desktop + mobile), so deduplicate by ISIN
    seen: set[str] = set()
    unique: list[Warrant] = []
    for w in results:
        if w.isin not in seen:
            seen.add(w.isin)
            unique.append(w)
    results = unique

    logger.info("Parsed %d warrants across %d page(s)", len(results), pages_fetched)
    return WarrantFinderResponse(url=url, count=len(results), results=results)
