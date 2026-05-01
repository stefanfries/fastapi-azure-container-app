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
        description=(
            "Include only off-market flat-fee warrants (comdirect Aktion). "
            "**Warning:** comdirect does not publish real-time analytics for off-market warrants. "
            "Combining this flag with Greek filters (delta_min/max, omega_min/max, etc.) "
            "may return fewer results than expected because warrants without analytics data "
            "are assigned a sentinel value by comdirect that can interfere with upper-bound filters."
        ),
    ),
    issuer_no_fee_action: bool = Query(
        False,
        description=(
            "Include only market no-fee warrants. "
            "**Warning:** see issuer_action — the same caveat about Greek filters applies."
        ),
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
        description=(
            "End of maturity range. Same format options as maturity_from. "
            "Defaults to None (no upper limit — all maturities included). "
            "Use Range_ENDLESS to filter for perpetual warrants only."
        ),
    ),
    issuer_group_id: str | None = Query(
        None,
        description="Comdirect issuer group ID (ID_GROUP_ISSUER).",
    ),
    delta_min: float | None = Query(
        None,
        description="Lower bound for Delta (DELTA > delta_min). E.g. 0.60 for Core Trend.",
    ),
    delta_max: float | None = Query(
        None,
        description="Upper bound for Delta (DELTA < delta_max). E.g. 0.75 for Core Trend.",
    ),
    omega_min: float | None = Query(
        None,
        description=(
            "Lower bound for Omega / effective leverage (GEARING > omega_min). "
            "E.g. 4 for Core Trend."
        ),
    ),
    omega_max: float | None = Query(
        None,
        description=(
            "Upper bound for Omega / effective leverage (GEARING < omega_max). "
            "E.g. 7 for Core Trend."
        ),
    ),
    moneyness_min: float | None = Query(
        None,
        description="Lower bound for Moneyness in % (MONEYNESS > moneyness_min). E.g. 95.",
    ),
    moneyness_max: float | None = Query(
        None,
        description="Upper bound for Moneyness in % (MONEYNESS < moneyness_max). E.g. 110.",
    ),
    premium_per_annum_max: float | None = Query(
        None,
        description="Upper bound for Premium p.a. in % (PREMIUM_PER_ANNUM < premium_per_annum_max). E.g. 18.",
    ),
    premium_per_annum_min: float | None = Query(
        None,
        description="Lower bound for Premium p.a. in % (PREMIUM_PER_ANNUM > premium_per_annum_min).",
    ),
    implied_volatility_min: float | None = Query(
        None,
        description="Lower bound for implied volatility in %.",
    ),
    implied_volatility_max: float | None = Query(
        None,
        description="Upper bound for implied volatility in %.",
    ),
    leverage_min: float | None = Query(
        None,
        description="Lower bound for Leverage (LEVERAGE > leverage_min).",
    ),
    leverage_max: float | None = Query(
        None,
        description="Upper bound for Leverage (LEVERAGE < leverage_max).",
    ),
    spread_ask_pct_min: float | None = Query(
        None,
        description="Lower bound for Spread/Ask % (SPREAD_ASK_PCT > spread_ask_pct_min).",
    ),
    spread_ask_pct_max: float | None = Query(
        None,
        description="Upper bound for Spread/Ask % (SPREAD_ASK_PCT < spread_ask_pct_max).",
    ),
    theta_day_min: float | None = Query(
        None,
        description="Lower bound for Theta/day (THETA_DAY > theta_day_min).",
    ),
    theta_day_max: float | None = Query(
        None,
        description="Upper bound for Theta/day (THETA_DAY < theta_day_max).",
    ),
    present_value_min: float | None = Query(
        None,
        description="Lower bound for Present Value (PRESENT_VALUE > present_value_min).",
    ),
    present_value_max: float | None = Query(
        None,
        description="Upper bound for Present Value (PRESENT_VALUE < present_value_max).",
    ),
    theoretical_value_min: float | None = Query(
        None,
        description="Lower bound for Theoretical Value (THEORETICAL_VALUE > theoretical_value_min).",
    ),
    theoretical_value_max: float | None = Query(
        None,
        description="Upper bound for Theoretical Value (THEORETICAL_VALUE < theoretical_value_max).",
    ),
    intrinsic_value_min: float | None = Query(
        None,
        description="Lower bound for Intrinsic Value (INTRINSIC_VALUE > intrinsic_value_min).",
    ),
    intrinsic_value_max: float | None = Query(
        None,
        description="Upper bound for Intrinsic Value (INTRINSIC_VALUE < intrinsic_value_max).",
    ),
    break_even_min: float | None = Query(
        None,
        description="Lower bound for Break Even (BREAK_EVEN > break_even_min).",
    ),
    break_even_max: float | None = Query(
        None,
        description="Upper bound for Break Even (BREAK_EVEN < break_even_max).",
    ),
    vega_min: float | None = Query(
        None,
        description="Lower bound for Vega (VEGA > vega_min).",
    ),
    vega_max: float | None = Query(
        None,
        description="Upper bound for Vega (VEGA < vega_max).",
    ),
    gamma_min: float | None = Query(
        None,
        description="Lower bound for Gamma (GAMMA > gamma_min).",
    ),
    gamma_max: float | None = Query(
        None,
        description="Upper bound for Gamma (GAMMA < gamma_max).",
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
        maturity_from:           Start of maturity range (Range_* code or date).
                                 Defaults to ``Range_NOW``.
        maturity_to:             End of maturity range (Range_* code or date).
        issuer_group_id:         Comdirect issuer group ID.
        delta_min:               Lower bound for Delta.
        delta_max:               Upper bound for Delta.
        omega_min:               Lower bound for Omega (effective leverage / GEARING).
        omega_max:               Upper bound for Omega (effective leverage / GEARING).
        moneyness_min:           Lower bound for Moneyness in %.
        moneyness_max:           Upper bound for Moneyness in %.
        premium_per_annum_max:   Upper bound for Premium p.a. in %.
        premium_per_annum_min:   Lower bound for Premium p.a. in %.
        implied_volatility_min:  Lower bound for implied volatility in %.
        implied_volatility_max:  Upper bound for implied volatility in %.
        leverage_min:            Lower bound for Leverage.
        leverage_max:            Upper bound for Leverage.
        spread_ask_pct_min:      Lower bound for Spread/Ask %.
        spread_ask_pct_max:      Upper bound for Spread/Ask %.
        theta_day_min:           Lower bound for Theta/day.
        theta_day_max:           Upper bound for Theta/day.
        present_value_min:       Lower bound for Present Value.
        present_value_max:       Upper bound for Present Value.
        theoretical_value_min:   Lower bound for Theoretical Value.
        theoretical_value_max:   Upper bound for Theoretical Value.
        intrinsic_value_min:     Lower bound for Intrinsic Value.
        intrinsic_value_max:     Upper bound for Intrinsic Value.
        break_even_min:          Lower bound for Break Even.
        break_even_max:          Upper bound for Break Even.
        vega_min:                Lower bound for Vega.
        vega_max:                Upper bound for Vega.
        gamma_min:               Lower bound for Gamma.
        gamma_max:               Upper bound for Gamma.

    Returns:
        :class:`WarrantFinderResponse` containing the constructed comdirect
        URL (for verification) and the list of matching warrants.
    """
    logger.info(
        "Warrant finder request: underlying=%s, preselection=%s, "
        "strike=[%s, %s], maturity=[%s, %s], "
        "delta=[%s, %s], omega=[%s, %s], moneyness=[%s, %s], "
        "premium_per_annum_max=%s, premium_per_annum_min=%s, iv=[%s, %s], "
        "leverage=[%s, %s], spread_ask_pct=[%s, %s], theta_day=[%s, %s], "
        "present_value=[%s, %s], theoretical_value=[%s, %s], intrinsic_value=[%s, %s], "
        "break_even=[%s, %s], vega=[%s, %s], gamma=[%s, %s]",
        underlying,
        preselection.value,
        strike_min,
        strike_max,
        maturity_from,
        maturity_to,
        delta_min,
        delta_max,
        omega_min,
        omega_max,
        moneyness_min,
        moneyness_max,
        premium_per_annum_max,
        premium_per_annum_min,
        implied_volatility_min,
        implied_volatility_max,
        leverage_min,
        leverage_max,
        spread_ask_pct_min,
        spread_ask_pct_max,
        theta_day_min,
        theta_day_max,
        present_value_min,
        present_value_max,
        theoretical_value_min,
        theoretical_value_max,
        intrinsic_value_min,
        intrinsic_value_max,
        break_even_min,
        break_even_max,
        vega_min,
        vega_max,
        gamma_min,
        gamma_max,
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
