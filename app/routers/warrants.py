"""
Router for the warrant (Optionsschein) endpoints.

Provides two endpoints:
    GET /v1/warrants/              — search for warrants on the comdirect Optionsschein Finder
    GET /v1/warrants/{identifier}  — detail page data for a single warrant by WKN or ISIN

Functions:
    get_warrants:       Search and return warrants matching the given selection criteria.
    get_warrant_detail: Return market data, analytics, and reference data for one warrant.

Dependencies:
    fastapi.APIRouter: Used to create the router for the warrant routes.
    app.logging_config.logger: Logger instance for logging information.
"""

from fastapi import APIRouter, Depends, Query

from app.core.logging import logger
from app.core.security import require_api_key
from app.models.warrants import (
    WarrantDetailResponse,
    WarrantFinderResponse,
    WarrantPreselection,
)
from app.parsers.warrant_detail import parse_warrant_detail
from app.parsers.warrants import fetch_warrants

router = APIRouter(
    prefix="/v1/warrants", tags=["warrants"], dependencies=[Depends(require_api_key)]
)


@router.get("/", response_model=WarrantFinderResponse)
async def get_warrants(
    underlying: str = Query(
        ...,
        description=(
            "WKN or ISIN of the underlying instrument, "
            "e.g. 'A2PWMJ' (NVIDIA WKN) or 'US67066G1040' (NVIDIA ISIN). "
            "The id_notation is resolved internally."
        ),
    ),
    preselection: WarrantPreselection = Query(
        WarrantPreselection.ALL,
        description="Warrant type filter: CALL, PUT, OTHER, or ALL. Defaults to ALL.",
    ),
    issuer_action: bool = Query(
        False,
        description="Include only off-market flat-fee warrants (comdirect Aktion).",
    ),
    issuer_no_fee_action: bool = Query(
        False,
        description="Include only market no-fee warrants.",
    ),
    strike_min: float | None = Query(
        None,
        description="Minimum strike price (STRIKE_ABS_FROM).",
    ),
    strike_max: float | None = Query(
        None,
        description="Maximum strike price (STRIKE_ABS_TO).",
    ),
    maturity_from: str | None = Query(
        None,
        description=(
            "Start of maturity range. "
            "Range codes: Range_NOW, Range_2W, Range_1M, Range_3M, Range_6M, Range_1Y, Range_2Y, Range_3Y, Range_5Y, Range_7Y, Range_ENDLESS."
            "Explicit dates: YYYY-MM-DD or DD.MM.YYYY. "
            "Defaults to Range_NOW."
        ),
    ),
    maturity_to: str | None = Query(
        None,
        description=("End of maturity range. Same format options as maturity_from."),
    ),
    issuer_group_id: str | None = Query(
        None,
        description="Comdirect issuer group ID (ID_GROUP_ISSUER).",
    ),
) -> WarrantFinderResponse:
    """Search and return warrants from the comdirect Optionsschein Finder.

    Resolves the underlying WKN or ISIN to a comdirect ``id_notation`` internally,
    constructs the finder URL, fetches the results page, and returns the results.

    **Note (step 1):** HTML result parsing is not yet implemented.  The response
    currently returns the constructed URL and an empty ``results`` list.
    Full parsing will be added in step 2 after HTML analysis.

    Args:
        underlying:           WKN or ISIN of the underlying instrument.
        preselection:         Warrant type filter.  Defaults to ``ALL``.
        issuer_action:        Include off-market flat-fee (Aktion) warrants.
        issuer_no_fee_action: Include market no-fee warrants.
        strike_min:           Minimum strike price.
        strike_max:           Maximum strike price.
        maturity_from:        Start of maturity range (Range_* code or date).
                              Defaults to ``Range_NOW``.
        maturity_to:          End of maturity range (Range_* code or date).
        issuer_group_id:      Comdirect issuer group ID.

    Returns:
        :class:`WarrantFinderResponse` containing the constructed comdirect
        URL (for verification) and the list of matching warrants.
    """
    logger.info(
        "Warrant finder request: underlying=%s, preselection=%s, "
        "strike=[%s, %s], maturity=[%s, %s]",
        underlying,
        preselection.value,
        strike_min,
        strike_max,
        maturity_from,
        maturity_to,
    )
    return await fetch_warrants(
        underlying=underlying,
        preselection=preselection,
        issuer_action=issuer_action,
        issuer_no_fee_action=issuer_no_fee_action,
        strike_min=strike_min,
        strike_max=strike_max,
        maturity_from=maturity_from,
        maturity_to=maturity_to,
        issuer_group_id=issuer_group_id,
    )


@router.get("/{identifier}", response_model=WarrantDetailResponse)
async def get_warrant_detail(identifier: str) -> WarrantDetailResponse:
    """Return market data, analytics, and reference data for a single warrant.

    Resolves the warrant's WKN or ISIN to a comdirect detail page and parses
    three groups of information:

    - **market_data** — live bid/ask prices, spread, OHLC, timestamp, venue
    - **analytics** — Greeks and derived key metrics (delta, omega, IV, theta, …)
    - **reference_data** — static attributes (strike, underlying, maturity, issuer, …)

    Args:
        identifier: WKN or ISIN of the **warrant itself** (not the underlying).

    Returns:
        :class:`WarrantDetailResponse` with ``market_data``, ``analytics``,
        and ``reference_data`` fields.
    """
    logger.info("Warrant detail request: identifier=%s", identifier)
    return await parse_warrant_detail(identifier)
