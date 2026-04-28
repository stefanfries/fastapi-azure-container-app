import asyncio
import re

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.constants import BASE_URL, asset_class_identifier_to_asset_class_map
from app.core.logging import logger
from app.models.indices import IndexInfo, IndexMember

INDEX_LIST_URL = f"{BASE_URL}/inf/index.html"

_ISIN_RE = re.compile(r"([A-Z]{2}[A-Z0-9]{10})$")


def _normalize_name(name: str) -> str:
    """Normalize an index name for lookup: strip non-alphanumeric, lowercase, collapse 'and'.

    Examples: 'S&P 500' -> 'sp500', 'SandP500' -> 'sp500', 'SP500' -> 'sp500',
              'DOW JONES' -> 'dowjones', 'L-DAX' -> 'ldax'
    """
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized.replace("and", "")


def _extract_isin_from_path(path: str) -> str | None:
    """Extract ISIN from the last segment of a URL path."""
    last_segment = path.rstrip("/").split("/")[-1]
    match = _ISIN_RE.search(last_segment)
    return match.group(1) if match else None


def _extract_asset_class_label(href: str) -> str | None:
    """Map comdirect URL path segment to AssetClass label."""
    parts = href.split("/")
    if len(parts) >= 3:
        identifier = parts[2]
        asset_class = asset_class_identifier_to_asset_class_map.get(identifier)
        return asset_class.value if asset_class else None
    return None


def _get_total_pages(soup: BeautifulSoup) -> int:
    """Return the total number of pages from the pagination widget, or 1 if none."""
    pager = soup.find("div", class_="pagination")
    if not pager:
        return 1
    page_numbers = [
        int(span.get_text(strip=True))
        for span in pager.find_all("span", class_="pagination__page")
        if span.get_text(strip=True).isdigit()
    ]
    return max(page_numbers) if page_numbers else 1


def _parse_members_from_table(soup: BeautifulSoup) -> list[IndexMember]:
    """Parse index members from the comparison table in a BeautifulSoup document."""
    table = soup.find("table", class_="table--comparison")
    if not table:
        return []
    members: list[IndexMember] = []
    for row in table.find_all("tr"):
        th = row.find("th")
        if not th:
            continue
        link_tag = th.find("a")
        if not link_tag:
            continue
        href = link_tag.get("href", "")
        if not href:
            continue
        isin = _extract_isin_from_path(href)
        if not isin:
            logger.warning("Could not extract ISIN from href '%s', skipping", href)
            continue
        members.append(
            IndexMember(
                name=link_tag.get_text(strip=True),
                isin=isin,
                link=f"{BASE_URL}{href}",
                asset_class=_extract_asset_class_label(href),
                instrument_url=f"/v1/instruments/{isin}",
            )
        )
    return members


async def _fetch_wkn(isin: str) -> str | None:
    """Fetch the WKN for an index from its comdirect detail page."""
    url = f"{BASE_URL}/inf/indizes/{isin}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        h2 = soup.find("h2")
        if h2 and "WKN:" in h2.text:
            return h2.text.split("WKN:")[1].strip()
    except Exception as e:
        logger.warning("Could not fetch WKN for ISIN %s: %s", isin, e)
    return None


async def fetch_index_list() -> list[IndexInfo]:
    """Scrape the comdirect index overview page and return supported indices."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(INDEX_LIST_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", id="indexes")
        if not table:
            logger.error("Index table (#indexes) not found on %s", INDEX_LIST_URL)
            raise HTTPException(status_code=502, detail="Index list table not found")

        # Collect name, link, ISIN, and member count for each valid row
        candidates: list[tuple[str, str, str, int]] = []  # (name, full_link, isin, member_count)
        for row in table.find_all("tr"):
            th = row.find("th")
            tds = row.find_all("td")
            if not th or not tds:
                continue
            link_tag = th.find("a")
            if not link_tag:
                continue
            href = link_tag.get("href", "")
            if not href:
                continue
            werte_text = tds[1].get_text(strip=True).replace(".", "").replace(",", "")
            if not werte_text.isdigit() or int(werte_text) == 0:
                continue
            isin = _extract_isin_from_path(href)
            if not isin:
                continue
            candidates.append(
                (
                    link_tag.get_text(strip=True),
                    f"{BASE_URL}{href}",
                    isin,
                    int(werte_text),
                )
            )

        # Fetch all WKNs in parallel (each with its own client to avoid pool exhaustion)
        wkns = await asyncio.gather(*[_fetch_wkn(isin) for _, _, isin, _ in candidates])

    result = [
        IndexInfo(name=name, wkn=wkn, member_count=member_count, link=link)
        for (name, link, _, member_count), wkn in zip(candidates, wkns)
    ]
    logger.info("Fetched %d indices from comdirect", len(result))
    return result


def _members_page_url(isin: str, offset: int = 0) -> str:
    """Build the comdirect paginated index-members URL for a given ISIN and offset."""
    return (
        f"{BASE_URL}/inf/indizes/detail/werte/standard.html"
        f"?OFFSET={offset}&ISIN={isin}"
        f"&SORT=SHORT_NAME_INSTRUMENT&SORTDIR=ASCENDING"
    )


async def _fetch_all_members(isin: str, label: str, expected_count: int | None = None) -> list[IndexMember]:
    """Fetch all paginated member rows for an index identified by ISIN."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        first_response = await client.get(_members_page_url(isin))
        first_response.raise_for_status()
        first_soup = BeautifulSoup(first_response.content, "html.parser")

        total_pages = _get_total_pages(first_soup)
        logger.info("Index '%s' has %d page(s)", label, total_pages)

        members = _parse_members_from_table(first_soup)

        if total_pages > 1:
            pages = await asyncio.gather(
                *[client.get(_members_page_url(isin, offset)) for offset in range(1, total_pages)]
            )
            for page_response in pages:
                page_response.raise_for_status()
                page_soup = BeautifulSoup(page_response.content, "html.parser")
                members.extend(_parse_members_from_table(page_soup))

    if expected_count is not None and len(members) != expected_count:
        logger.warning(
            "Member count mismatch for '%s': expected %d from overview, fetched %d",
            label,
            expected_count,
            len(members),
        )
    else:
        logger.info("Fetched %d members for '%s'", len(members), label)

    return members


async def fetch_index_members(index_name: str) -> list[IndexMember]:
    """Fetch all members of a named index from comdirect, handling pagination.

    ``index_name`` may be a human-readable name (e.g. ``"DAX"``), a WKN
    (e.g. ``"846900"``), or an ISIN (e.g. ``"DE0008469008"``).  Name matching
    is case-insensitive and ignores punctuation (see ``_normalize_name``).

    When an ISIN is provided that does not appear in the comdirect index
    catalogue URL (e.g. a German tracking ISIN for the S&P 500), members are
    fetched directly from comdirect using that ISIN as the pagination key,
    bypassing the catalogue entirely.
    """
    indices = await fetch_index_list()

    # Primary lookup: normalised name match
    match = next(
        (idx for idx in indices if _normalize_name(idx.name) == _normalize_name(index_name)),
        None,
    )

    # Secondary lookup: match the ISIN embedded in the catalogue link URL
    if match is None and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", index_name.upper()):
        isin_upper = index_name.upper()
        match = next(
            (idx for idx in indices if _extract_isin_from_path(idx.link) == isin_upper),
            None,
        )

    # Catalogue match found — use its link and expected member count
    if match is not None:
        isin = _extract_isin_from_path(match.link)
        if not isin:
            raise HTTPException(status_code=502, detail="Could not determine ISIN for pagination")
        logger.info(
            "Fetching members for index '%s' (expected: %d) via catalogue",
            match.name,
            match.member_count,
        )
        return await _fetch_all_members(isin, label=match.name, expected_count=match.member_count)

    # Final fallback: ISIN supplied directly (e.g. from constituents_url) but not
    # present in the catalogue link — fetch members directly using that ISIN.
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", index_name.upper()):
        logger.info(
            "ISIN '%s' not found in catalogue; fetching members directly from comdirect",
            index_name,
        )
        return await _fetch_all_members(index_name.upper(), label=index_name)

    raise HTTPException(
        status_code=404,
        detail=f"Index '{index_name}' not found. "
        f"Supported indices: {[i.name for i in indices]}",
    )
