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
_OPENFIGI_SEARCH_URL = "https://api.openfigi.com/v3/search"


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


async def search_by_name(name: str, exch_code: str | None = None) -> list[dict[str, Any]]:
    """
    Search OpenFIGI for equity records by company name via the v3 search API.

    Used to locate the primary common-stock listing of a company when only its
    name is known (e.g. to map an ADR back to its underlying ordinary share).
    Results are restricted to common stock (``securityType2="Common Stock"``).

    Args:
        name: Company name to search for (e.g. "ASML HOLDING NV").
        exch_code: Optional OpenFIGI exchange code filter (e.g. "GY" for Xetra).
                   When given, only listings on that exchange are returned.

    Returns:
        List of FIGI result dicts. Empty list if not found or on error.
    """
    body: dict[str, Any] = {"query": name, "securityType2": "Common Stock"}
    if exch_code:
        body["exchCode"] = exch_code
    return await _search(body)


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
        logger.warning("OpenFIGI HTTP error %s — skipping enrichment", exc.response.status_code)
        return []
    except httpx.RequestError as exc:
        logger.warning("OpenFIGI request failed (%s) — skipping enrichment", exc)
        return []


async def _search(body: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Send a search request to the OpenFIGI v3 search API and return the data list.

    Never raises — all HTTP and network errors are caught and logged. Unlike the
    mapping endpoint, the search endpoint returns a single result object (not an
    array of per-job results).

    Args:
        body: Search request object (query plus optional filters).

    Returns:
        List of FIGI records. Empty list on warning, error, or failure.
    """
    settings = get_settings()
    headers: dict[str, str] = {"Content-Type": "application/json"}

    api_key = settings.openfigi.api_key
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key.get_secret_value()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(_OPENFIGI_SEARCH_URL, json=body, headers=headers)

        if response.status_code == 429:
            logger.warning("OpenFIGI rate limit reached — skipping search")
            return []

        response.raise_for_status()
        result: dict[str, Any] = response.json()

        if "warning" in result:
            logger.debug("OpenFIGI search: no match — %s", result["warning"])
            return []

        if "error" in result:
            logger.warning("OpenFIGI search error: %s", result["error"])
            return []

        return result.get("data", [])

    except httpx.HTTPStatusError as exc:
        logger.warning("OpenFIGI HTTP error %s — skipping search", exc.response.status_code)
        return []
    except httpx.RequestError as exc:
        logger.warning("OpenFIGI search request failed (%s) — skipping search", exc)
        return []
