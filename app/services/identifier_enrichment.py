"""
Identifier enrichment service.

Derives and fetches additional global identifiers (CUSIP, FIGI, yfinance symbol,
OpenFIGI name) for financial instruments by combining locally-computed values
with data from the OpenFIGI API.

Enrichment is intentionally skipped for WARRANT and CERTIFICATE asset classes
because structured products (Warrants, Certificates) are not listed on Yahoo
Finance and OpenFIGI returns no useful data for them.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from app.clients import openfigi as openfigi_client
from app.core.logging import logger
from app.models.instruments import AssetClass, GlobalIdentifiers

# Asset classes for which OpenFIGI enrichment is skipped.
# Warrants and Certificates are OTC structured products not available on Yahoo Finance.
_SKIP_ENRICHMENT_FOR: frozenset[AssetClass] = frozenset(
    {AssetClass.WARRANT, AssetClass.CERTIFICATE}
)

# Maps OpenFIGI exchCode values to Yahoo Finance ticker suffixes.
# Instruments on US exchanges use no suffix.
_EXCH_TO_YAHOO_SUFFIX: dict[str, str] = {
    # United States (NYSE, NASDAQ, AMEX, …)
    "US": "",
    "UN": "",
    "UQ": "",
    "UA": "",
    "UP": "",
    # Germany
    "GY": ".DE",  # Xetra
    "GF": ".F",  # Frankfurt
    "GS": ".SG",  # Stuttgart
    "GM": ".MU",  # München
    "GH": ".HM",  # Hamburg
    "GD": ".DU",  # Düsseldorf
    "GW": ".BE",  # Berlin
    "GX": ".HA",  # Hannover
    # Europe
    "LN": ".L",  # London Stock Exchange
    "SW": ".SW",  # SIX Swiss Exchange
    "AV": ".VI",  # Wiener Börse
    "FP": ".PA",  # Euronext Paris
    "NA": ".AS",  # Euronext Amsterdam
    "BB": ".BR",  # Euronext Brussels
    # Asia-Pacific
    "JT": ".T",  # Tokyo Stock Exchange
    "HK": ".HK",  # Hong Kong Stock Exchange
    "AU": ".AX",  # ASX
}

# Maps two-letter ISIN country code to the primary OpenFIGI exchCode for that country.
# Used to pick the home-exchange record when no US listing is found.
_ISIN_COUNTRY_TO_PRIMARY_EXCH: dict[str, str] = {
    "US": "US",
    "DE": "GY",
    "GB": "LN",
    "CH": "SW",
    "AT": "AV",
    "FR": "FP",
    "NL": "NA",
    "BE": "BB",
    "JP": "JT",
    "HK": "HK",
    "AU": "AU",
}

_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


@dataclass(frozen=True)
class MappingOverride:
    """Auditable mapping override for exceptional ISIN-to-symbol corrections."""

    symbol_yfinance: str
    owner: str
    reason: str
    updated_at: str


# Server-side correction table for known mapping anomalies.
_ISIN_SYMBOL_OVERRIDES: dict[str, MappingOverride] = {
    "US74743L1008": MappingOverride(
        symbol_yfinance="BG",
        owner="data-quality-team",
        reason="OpenFIGI returned stale/wrong symbols (Q23, Q23.SW) for Bunge Global S.A.",
        updated_at="2026-07-19T00:00:00Z",
    ),
    "CH0044328745": MappingOverride(
        symbol_yfinance="CB",
        owner="data-quality-team",
        reason="Chubb should resolve to primary US listing on Yahoo Finance.",
        updated_at="2026-07-19T00:00:00Z",
    ),
    "CH0114405324": MappingOverride(
        symbol_yfinance="GRMN",
        owner="data-quality-team",
        reason="Garmin should resolve to primary US listing on Yahoo Finance.",
        updated_at="2026-07-19T00:00:00Z",
    ),
}


def _derive_cusip(isin: str | None) -> str | None:
    """
    Derive CUSIP from a US ISIN.

    For US instruments the ISIN is built as "US" + CUSIP (9 chars) + check digit.
    CUSIP = isin[2:11].

    Args:
        isin: ISIN string, or None.

    Returns:
        9-character CUSIP string for US instruments, None for all others.
    """
    if isin and isin.startswith("US") and len(isin) == 12:
        return isin[2:11]
    return None


def _pick_composite_figi(records: list[dict[str, Any]]) -> str | None:
    """
    Select the best compositeFIGI from a list of OpenFIGI mapping records.

    Preference order:
    1. US-listed equity record (most canonical for cross-listed instruments)
    2. First record that has a non-null compositeFIGI

    Args:
        records: List of raw FIGI record dicts from the OpenFIGI API.

    Returns:
        compositeFIGI string, or None if unavailable.
    """
    if not records:
        return None

    us_exch_codes = {"US", "UN", "UQ", "UA", "UP"}

    for rec in records:
        if rec.get("exchCode") in us_exch_codes and rec.get("compositeFIGI"):
            return rec["compositeFIGI"]

    for rec in records:
        if rec.get("compositeFIGI"):
            return rec["compositeFIGI"]

    return None


def _pick_name(records: list[dict[str, Any]]) -> str | None:
    """
    Extract the instrument name from the first OpenFIGI record that has one.

    Args:
        records: List of raw FIGI record dicts from the OpenFIGI API.

    Returns:
        Name string (e.g. "NVIDIA CORP"), or None if unavailable.
    """
    for rec in records:
        name = rec.get("name")
        if name:
            return name
    return None


def _rank_yfinance_candidates(
    records: list[dict[str, Any]], isin_country: str | None
) -> list[tuple[str, str]]:
    """Build deterministically ordered Yahoo symbol candidates with ranking reasons."""
    if not records:
        return []

    us_exch_codes = {"US", "UN", "UQ", "UA", "UP"}
    seen: set[str] = set()

    def _to_yahoo_symbol(record: dict[str, Any]) -> str | None:
        exch = record.get("exchCode", "")
        ticker = record.get("ticker")
        if not ticker or exch not in _EXCH_TO_YAHOO_SUFFIX:
            return None
        suffix = _EXCH_TO_YAHOO_SUFFIX[exch]
        return f"{ticker.replace('/', '-')}{suffix}"

    def _append_candidates(filtered: list[dict[str, Any]], reason: str) -> list[tuple[str, str]]:
        ranked: list[tuple[str, str]] = []
        for rec in filtered:
            symbol = _to_yahoo_symbol(rec)
            if symbol and symbol not in seen:
                seen.add(symbol)
                ranked.append((symbol, reason))
        return ranked

    ranked_candidates: list[tuple[str, str]] = []

    # Priority 1: home exchange from ISIN prefix when available.
    if isin_country and isin_country in _ISIN_COUNTRY_TO_PRIMARY_EXCH:
        home_exch = _ISIN_COUNTRY_TO_PRIMARY_EXCH[isin_country]
        ranked_candidates.extend(
            _append_candidates(
                [rec for rec in records if rec.get("exchCode") == home_exch],
                "home_exchange",
            )
        )

    # Priority 2: any US listing as global fallback.
    ranked_candidates.extend(
        _append_candidates(
            [rec for rec in records if rec.get("exchCode") in us_exch_codes],
            "us_listing_fallback",
        )
    )

    # Priority 3: first remaining known Yahoo-mapped exchanges.
    ranked_candidates.extend(
        _append_candidates(
            [
                rec
                for rec in records
                if rec.get("exchCode") in _EXCH_TO_YAHOO_SUFFIX
                and rec.get("exchCode") not in us_exch_codes
            ],
            "known_exchange_fallback",
        )
    )

    return ranked_candidates


def _derive_yfinance_symbol(records: list[dict[str, Any]], isin_country: str | None) -> str | None:
    """
    Derive the yfinance-compatible ticker symbol from OpenFIGI mapping records.

    Priority order:
    1. Record whose exchange matches the instrument's home country (from ISIN prefix).
       US stocks land here too: isin_country "US" → exchCode "US" → no suffix.
    2. Any US-listed record — fallback when the country is unknown or unmapped.
    3. First record whose exchCode maps to a known Yahoo Finance suffix.

    OpenFIGI uses "/" for share-class separators (e.g. "BF/B"), but Yahoo Finance
    uses "-" (e.g. "BF-B"). All "/" characters in the ticker are replaced with "-".

    Args:
        records: List of raw FIGI record dicts from the OpenFIGI API.
        isin_country: Two-letter country code from the ISIN prefix (e.g. "DE", "US").
                      None if no ISIN is available.

    Returns:
        Yahoo Finance-compatible ticker string (e.g. "NVDA", "SIE.DE", "BF-B"), or None.
    """
    ranked = _rank_yfinance_candidates(records, isin_country)
    if not ranked:
        return None
    return ranked[0][0]


async def _has_recent_yahoo_prices(symbol: str) -> bool:
    """Return True when Yahoo chart endpoint provides recent timestamps for *symbol*."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                _YAHOO_CHART_URL.format(symbol=symbol),
                params={"range": "5d", "interval": "1d"},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("yahoo_validation_error symbol=%s error=%s", symbol, exc)
        return False

    chart = payload.get("chart", {})
    result = chart.get("result")
    if not result or not isinstance(result, list):
        return False

    timestamps = result[0].get("timestamp") if result else None
    return isinstance(timestamps, list) and len(timestamps) > 0


async def _select_yfinance_symbol(
    isin: str | None,
    records: list[dict[str, Any]],
    isin_country: str | None,
) -> tuple[str | None, str | None]:
    """Select and validate yfinance symbol using overrides, ranking, and chart availability."""
    if isin and isin in _ISIN_SYMBOL_OVERRIDES:
        override = _ISIN_SYMBOL_OVERRIDES[isin]
        logger.info(
            "mapping_override_applied isin=%s symbol=%s owner=%s reason=%s updated_at=%s",
            isin,
            override.symbol_yfinance,
            override.owner,
            override.reason,
            override.updated_at,
        )
        return override.symbol_yfinance, "known_override"

    ranked = _rank_yfinance_candidates(records, isin_country)
    if not ranked:
        logger.warning("mapping_unresolved_no_candidates isin=%s", isin)
        return None, None

    primary_symbol, primary_reason = ranked[0]
    primary_valid = await _has_recent_yahoo_prices(primary_symbol)
    if primary_valid:
        return primary_symbol, primary_reason

    for candidate_symbol, candidate_reason in ranked[1:]:
        if await _has_recent_yahoo_prices(candidate_symbol):
            logger.warning(
                "mapping_corrected_by_validation isin=%s from=%s to=%s from_reason=%s to_reason=%s",
                isin,
                primary_symbol,
                candidate_symbol,
                primary_reason,
                candidate_reason,
            )
            return candidate_symbol, candidate_reason

    logger.warning(
        "mapping_validation_fallback isin=%s symbol=%s reason=%s",
        isin,
        primary_symbol,
        primary_reason,
    )
    return primary_symbol, primary_reason


async def build_global_identifiers(
    isin: str | None,
    wkn: str | None,
    symbol_comdirect: str | None,
    asset_class: AssetClass,
) -> GlobalIdentifiers:
    """
    Build a GlobalIdentifiers object for a financial instrument.

    Performs OpenFIGI enrichment for supported asset classes to obtain the
    composite FIGI and the yfinance-compatible ticker symbol. For WARRANT and
    CERTIFICATE the enrichment step is skipped entirely and figi/symbol_yfinance
    are left as None.

    If the OpenFIGI call fails for any reason (rate limit, network error), the
    function still returns a valid GlobalIdentifiers object with figi=None and
    symbol_yfinance=None. This prevents enrichment failures from blocking the
    instrument data response.

    Args:
        isin: ISIN string, or None if the instrument has no ISIN.
        wkn: WKN string, or None for foreign instruments without a WKN.
        symbol_comdirect: Ticker symbol as displayed on comdirect.de.
        asset_class: Asset class of the instrument.

    Returns:
        Populated GlobalIdentifiers instance.
    """
    cusip = _derive_cusip(isin)
    figi: str | None = None
    symbol_yfinance: str | None = None
    name_openfigi: str | None = None

    if asset_class not in _SKIP_ENRICHMENT_FOR:
        logger.debug(
            "Fetching OpenFIGI identifiers for asset_class=%s ISIN=%s WKN=%s",
            asset_class,
            isin,
            wkn,
        )
        try:
            if isin:
                records = await openfigi_client.map_by_isin(isin)
            elif wkn:
                logger.debug("No ISIN available — falling back to WKN for OpenFIGI lookup")
                records = await openfigi_client.map_by_wkn(wkn)
            else:
                logger.debug("No ISIN or WKN available — skipping OpenFIGI lookup")
                records = []
        except Exception as exc:
            logger.warning("openfigi_lookup_failed isin=%s wkn=%s error=%s", isin, wkn, exc)
            records = []

        figi = _pick_composite_figi(records)
        isin_country = isin[:2] if isin and len(isin) >= 2 else None
        symbol_yfinance, mapping_source = await _select_yfinance_symbol(isin, records, isin_country)
        name_openfigi = _pick_name(records)

        logger.debug(
            "OpenFIGI enrichment result: figi=%s symbol_yfinance=%s source=%s name=%s",
            figi,
            symbol_yfinance,
            mapping_source,
            name_openfigi,
        )
    else:
        logger.debug(
            "Skipping OpenFIGI enrichment for asset_class=%s (not on Yahoo Finance)",
            asset_class,
        )

    return GlobalIdentifiers(
        isin=isin,
        wkn=wkn,
        cusip=cusip,
        figi=figi,
        symbol_comdirect=symbol_comdirect,
        symbol_yfinance=symbol_yfinance,
        name_openfigi=name_openfigi,
    )
