"""
Async HTTP client for the OpenFIGI v3 Mapping API.

Handles low-level communication only — no business logic.
Callers receive a list of raw FIGI record dicts (may be empty).

Rate limits:
    Without API key : 25 requests / minute,     max 10  jobs per request
    With API key    : 25 requests / 6 seconds,  max 100 jobs per request

Docs: https://www.openfigi.com/api/documentation
"""

from typing import Any

import httpx

from app.core.logging import logger
from app.core.settings import get_settings

_OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"


async def map_by_isin(isin: str) -> list[dict[str, Any]]:
    """
    Map an ISIN to FIGI records via the OpenFIGI v3 mapping API.

    Args:
        isin: The ISIN to look up (e.g. "US67066G1040").

    Returns:
        List of FIGI result dicts for the instrument. Empty list if not found or on error.
    """
    return await _map([{"idType": "ID_ISIN", "idValue": isin, "marketSecDes": "Equity"}])


async def map_by_wkn(wkn: str) -> list[dict[str, Any]]:
    """
    Map a WKN (German securities identifier) to FIGI records via the OpenFIGI v3 mapping API.

    Used as fallback when no ISIN is available.

    Args:
        wkn: The WKN to look up (e.g. "918422").

    Returns:
        List of FIGI result dicts for the instrument. Empty list if not found or on error.
    """
    return await _map([{"idType": "ID_WERTPAPIER", "idValue": wkn, "marketSecDes": "Equity"}])


async def _map(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Send a mapping request to the OpenFIGI API and return the data list for the first job.

    Never raises — all HTTP and network errors are caught and logged.

    Args:
        jobs: List of mapping job objects. Only the first job's result is returned.

    Returns:
        List of FIGI records for the first job. Empty list on warning, error, or failure.
    """
    settings = get_settings()
    headers: dict[str, str] = {"Content-Type": "application/json"}

    api_key = settings.openfigi.api_key
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key.get_secret_value()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(_OPENFIGI_URL, json=jobs, headers=headers)

        if response.status_code == 429:
            logger.warning("OpenFIGI rate limit reached — skipping enrichment")
            return []

        response.raise_for_status()
        results: list[dict[str, Any]] = response.json()
        first = results[0] if results else {}

        if "warning" in first:
            # "No identifier found." is a normal outcome, not an error
            logger.debug("OpenFIGI: no match — %s", first["warning"])
            return []

        if "error" in first:
            logger.warning("OpenFIGI mapping error: %s", first["error"])
            return []

        return first.get("data", [])

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "OpenFIGI HTTP error %s — skipping enrichment", exc.response.status_code
        )
        return []
    except httpx.RequestError as exc:
        logger.warning("OpenFIGI request failed (%s) — skipping enrichment", exc)
        return []
