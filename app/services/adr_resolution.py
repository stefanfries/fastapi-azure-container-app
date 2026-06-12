"""
ADR-to-primary resolution service.

Some index constituent lists (e.g. NASDAQ-100) reference a company by its
American Depositary Receipt (ADR) rather than its primary ordinary share. ADRs
carry their own ISIN (e.g. ASML ``USN070592100``) for which no warrants or other
comdirect derivatives exist — those are only issued against the primary listing
(e.g. ASML ``NL0010273215``).

This service maps an ADR instrument back to its underlying primary listing:

    1. Search OpenFIGI by company name for the common-stock listing, preferring
       Xetra (the exchange comdirect natively trades) and falling back to the
       ADR's own home country.
    2. Resolve each candidate ticker on comdirect to a full instrument.
    3. Verify the resolved instrument is a non-ADR stock before accepting it.

If no primary listing can be confidently resolved, ``None`` is returned and the
caller is expected to drop the ADR entry.
"""

import re
from typing import Any

from app.clients import openfigi as openfigi_client
from app.core.logging import logger
from app.models.instruments import AssetClass, Instrument

# Matches "ADR" as a standalone token in a comdirect display name, e.g.
# "ASML ADR", "Arm Holdings ADR", "PINDUODUO INC. SP.ADR/4". Used as a cheap
# pre-filter so only likely ADR members trigger a detail-page lookup.
_ADR_NAME_RE = re.compile(r"\bADR\b", re.IGNORECASE)

# Depositary-receipt / share-registration suffixes that OpenFIGI appends to the
# issuer name (e.g. "ASML HOLDING NV-NY REG SHS", "ALIBABA GROUP-SP ADR"). These
# break a name search for the underlying common stock and must be stripped.
_NAME_SUFFIX_RE = re.compile(
    r"\s*[-/]?\s*\b("
    r"SP(?:ONS|ON)?\.?\s*ADR|UNSPON\.?\s*ADR|ADR|ADS|"
    r"NY\s*REG\s*SH(?:R)?S?|REG\s*SH(?:R)?S?|CDR|GDR"
    r")\b.*$",
    re.IGNORECASE,
)

# comdirect's native exchange (Xetra). Foreign index constituents almost always
# have a Xetra listing, so this is tried first when searching for the primary.
_XETRA_EXCH_CODE = "GY"

# Maps two-letter ISIN country code to the primary OpenFIGI exchCode for that
# country. Used as a fallback when no Xetra common-stock listing is found.
_ISIN_COUNTRY_TO_PRIMARY_EXCH: dict[str, str] = {
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

# Maximum number of distinct candidate tickers resolved against comdirect.
_MAX_CANDIDATES = 3

# comdirect Wertpapiertyp value identifying an ADR.
_ADR_SECURITY_TYPE = "ADR"


def is_adr(instrument: Instrument) -> bool:
    """Return True if *instrument* is a stock whose security type is ADR."""
    return (
        instrument.asset_class == AssetClass.STOCK
        and instrument.details is not None
        and getattr(instrument.details, "security_type", None) == _ADR_SECURITY_TYPE
    )


def _normalize_company_name(name: str) -> str:
    """Strip depositary-receipt / registration suffixes from an issuer name.

    OpenFIGI names ADRs as e.g. "ASML HOLDING NV-NY REG SHS" or
    "ALIBABA GROUP-SP ADR"; the suffix must be removed before searching for the
    underlying common stock. comdirect names such as "ASML ADR" are reduced to
    "ASML".
    """
    cleaned = _NAME_SUFFIX_RE.sub("", name).strip()
    # Drop a dangling separator left behind (e.g. "ASML HOLDING NV-")
    cleaned = cleaned.rstrip(" -/.")
    return cleaned or name


def _company_name(instrument: Instrument) -> str | None:
    """Pick the best company name for an OpenFIGI search.

    Prefers the OpenFIGI name (canonical, e.g. "ASML HOLDING NV") and falls back
    to the comdirect display name. Depositary-receipt suffixes are stripped.
    """
    gid = instrument.global_identifiers
    raw = gid.name_openfigi if gid is not None and gid.name_openfigi else instrument.name
    if not raw:
        return None
    return _normalize_company_name(raw)


def _candidate_tickers(records: list[dict[str, Any]]) -> list[str]:
    """Extract distinct, order-preserving tickers from OpenFIGI search records."""
    tickers: list[str] = []
    for rec in records:
        ticker = rec.get("ticker")
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers


async def _collect_candidate_tickers(name: str, isin: str | None) -> list[str]:
    """Search OpenFIGI for the company's common-stock tickers.

    Tries Xetra first (comdirect's native exchange), then the ADR's home country
    exchange, returning a bounded, de-duplicated, order-preserving list.
    """
    exch_codes: list[str] = [_XETRA_EXCH_CODE]
    isin_country = isin[:2] if isin and len(isin) >= 2 else None
    home_exch = _ISIN_COUNTRY_TO_PRIMARY_EXCH.get(isin_country) if isin_country else None
    if home_exch and home_exch not in exch_codes:
        exch_codes.append(home_exch)

    tickers: list[str] = []
    for exch_code in exch_codes:
        records = await openfigi_client.search_by_name(name, exch_code=exch_code)
        for ticker in _candidate_tickers(records):
            if ticker not in tickers:
                tickers.append(ticker)
        if len(tickers) >= _MAX_CANDIDATES:
            break
    return tickers[:_MAX_CANDIDATES]


async def resolve_adr_to_primary(adr_instrument: Instrument) -> str | None:
    """Resolve an ADR instrument to its primary (non-ADR) stock ISIN.

    Args:
        adr_instrument: An already-parsed instrument with ``security_type == "ADR"``.

    Returns:
        The primary listing's ISIN, or ``None`` if no primary listing could be
        confidently resolved.
    """
    name = _company_name(adr_instrument)
    if not name:
        logger.debug("ADR resolution: no company name available for %s", adr_instrument.isin)
        return None

    tickers = await _collect_candidate_tickers(name, adr_instrument.isin)
    if not tickers:
        logger.info("ADR resolution: no OpenFIGI common-stock match for '%s'", name)
        return None

    # Imported lazily to avoid a circular import (the instruments parser imports
    # this service to redirect ADRs).
    from app.parsers.instruments import parse_instrument_data

    for ticker in tickers:
        try:
            primary = await parse_instrument_data(ticker, _allow_adr_redirect=False)
        except Exception as exc:  # noqa: BLE001 — a bad ticker must not abort resolution
            logger.debug("ADR resolution: ticker '%s' did not resolve (%s)", ticker, exc)
            continue

        if primary.asset_class != AssetClass.STOCK or is_adr(primary):
            logger.debug(
                "ADR resolution: ticker '%s' resolved to %s (security_type=%s) — rejected",
                ticker,
                primary.asset_class,
                getattr(primary.details, "security_type", None),
            )
            continue

        if primary.isin and primary.isin != adr_instrument.isin:
            logger.info(
                "ADR resolution: %s (ADR) -> %s (%s) via ticker '%s'",
                adr_instrument.isin,
                primary.isin,
                primary.name,
                ticker,
            )
            return primary.isin

    logger.info("ADR resolution: no verified primary listing for '%s'", name)
    return None


def looks_like_adr_name(name: str) -> bool:
    """Cheap heuristic: True if a display name contains 'ADR' as a token."""
    return bool(_ADR_NAME_RE.search(name))


async def resolve_member_isin(name: str, isin: str) -> str | None:
    """Return the primary-listing ISIN for an index member, or ``None`` to drop it.

    Most members are returned unchanged: the ISIN is only re-resolved when the
    member's display name looks like an ADR *and* its comdirect detail page
    confirms ``security_type == "ADR"``.

    Args:
        name: Member display name from the comdirect index table.
        isin: Member ISIN from the comdirect index table.

    Returns:
        - The original ISIN when the member is not an ADR.
        - The primary listing's ISIN when an ADR is successfully resolved.
        - ``None`` when the member is an ADR with no resolvable primary listing
          (caller should omit the entry).
    """
    if not looks_like_adr_name(name):
        return isin

    # Imported lazily to avoid a circular import (the instruments parser imports
    # this service to redirect ADRs).
    from app.parsers.instruments import parse_instrument_data

    try:
        instrument = await parse_instrument_data(isin, _allow_adr_redirect=False)
    except Exception as exc:  # noqa: BLE001 — a lookup failure must not drop a valid member
        logger.debug("ADR pre-check: could not parse member %s (%s)", isin, exc)
        return isin

    if not is_adr(instrument):
        return isin

    return await resolve_adr_to_primary(instrument)
