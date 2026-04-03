"""
Identifier enrichment service.

Derives and fetches additional global identifiers (CUSIP, FIGI, yfinance symbol)
for financial instruments by combining locally-computed values with data from
the OpenFIGI API.

Enrichment is intentionally skipped for WARRANT and CERTIFICATE asset classes
because German-style structured products (Optionsscheine, Zertifikate) are not
listed on Yahoo Finance and OpenFIGI returns no useful data for them.
"""

from typing import Any, Optional

from app.clients import openfigi as openfigi_client
from app.logging_config import logger
from app.models.instruments import AssetClass, GlobalIdentifiers

# Asset classes for which OpenFIGI enrichment is skipped.
# German Optionsscheine and Zertifikate are OTC structured products not
# available on Yahoo Finance.
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
    "GY": ".DE",   # Xetra
    "GF": ".F",    # Frankfurt
    "GS": ".SG",   # Stuttgart
    "GM": ".MU",   # München
    "GH": ".HM",   # Hamburg
    "GD": ".DU",   # Düsseldorf
    "GW": ".BE",   # Berlin
    "GX": ".HA",   # Hannover
    # Europe
    "LN": ".L",    # London Stock Exchange
    "SW": ".SW",   # SIX Swiss Exchange
    "AV": ".VI",   # Wiener Börse
    "FP": ".PA",   # Euronext Paris
    "NA": ".AS",   # Euronext Amsterdam
    "BB": ".BR",   # Euronext Brussels
    # Asia-Pacific
    "JT": ".T",    # Tokyo Stock Exchange
    "HK": ".HK",   # Hong Kong Stock Exchange
    "AU": ".AX",   # ASX
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


def _derive_cusip(isin: Optional[str]) -> Optional[str]:
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


def _pick_composite_figi(records: list[dict[str, Any]]) -> Optional[str]:
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


def _derive_yfinance_symbol(
    records: list[dict[str, Any]], isin_country: Optional[str]
) -> Optional[str]:
    """
    Derive the yfinance-compatible ticker symbol from OpenFIGI mapping records.

    Priority order:
    1. US-listed record (e.g. "NVDA" for NVIDIA) — no suffix needed
    2. Record whose exchange matches the instrument's home country (from ISIN prefix)
    3. First record whose exchCode maps to a known Yahoo Finance suffix

    Args:
        records: List of raw FIGI record dicts from the OpenFIGI API.
        isin_country: Two-letter country code from the ISIN prefix (e.g. "DE", "US").
                      None if no ISIN is available.

    Returns:
        Yahoo Finance-compatible ticker string (e.g. "NVDA", "SIE.DE"), or None.
    """
    if not records:
        return None

    us_exch_codes = {"US", "UN", "UQ", "UA", "UP"}

    # Build (ticker, suffix, exchCode) candidates for all known exchanges
    candidates: list[tuple[str, str, str]] = []
    for rec in records:
        exch = rec.get("exchCode", "")
        ticker = rec.get("ticker")
        if ticker and exch in _EXCH_TO_YAHOO_SUFFIX:
            candidates.append((ticker, _EXCH_TO_YAHOO_SUFFIX[exch], exch))

    if not candidates:
        return None

    # Priority 1: US exchange (no suffix)
    for ticker, suffix, exch in candidates:
        if exch in us_exch_codes:
            return ticker

    # Priority 2: home exchange matching ISIN country code
    if isin_country and isin_country in _ISIN_COUNTRY_TO_PRIMARY_EXCH:
        home_exch = _ISIN_COUNTRY_TO_PRIMARY_EXCH[isin_country]
        for ticker, suffix, exch in candidates:
            if exch == home_exch:
                return f"{ticker}{suffix}"

    # Priority 3: first known-exchange candidate
    ticker, suffix, _ = candidates[0]
    return f"{ticker}{suffix}"


async def build_global_identifiers(
    isin: Optional[str],
    wkn: str,
    symbol_comdirect: Optional[str],
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
        wkn: WKN string (always present, used as fallback for OpenFIGI lookup).
        symbol_comdirect: Ticker symbol as displayed on comdirect.de.
        asset_class: Asset class of the instrument.

    Returns:
        Populated GlobalIdentifiers instance.
    """
    cusip = _derive_cusip(isin)
    figi: Optional[str] = None
    symbol_yfinance: Optional[str] = None

    if asset_class not in _SKIP_ENRICHMENT_FOR:
        logger.debug(
            "Fetching OpenFIGI identifiers for asset_class=%s ISIN=%s WKN=%s",
            asset_class,
            isin,
            wkn,
        )
        if isin:
            records = await openfigi_client.map_by_isin(isin)
        else:
            logger.debug("No ISIN available — falling back to WKN for OpenFIGI lookup")
            records = await openfigi_client.map_by_wkn(wkn)

        figi = _pick_composite_figi(records)
        isin_country = isin[:2] if isin and len(isin) >= 2 else None
        symbol_yfinance = _derive_yfinance_symbol(records, isin_country)

        logger.debug(
            "OpenFIGI enrichment result: figi=%s symbol_yfinance=%s", figi, symbol_yfinance
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
    )
