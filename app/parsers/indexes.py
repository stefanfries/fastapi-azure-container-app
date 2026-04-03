import asyncio
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.constants import BASE_URL, asset_class_identifier_to_asset_class_map
from app.logging_config import logger
from app.models.indexes import IndexInfo, IndexMember

INDEX_LIST_URL = f"{BASE_URL}/inf/index.html"
INDEX_MEMBERS_PAGE_URL = (
    f"{BASE_URL}/inf/indizes/detail/werte/standard.html"
    "?OFFSET={{offset}}&ISIN={{isin}}&SORT=SHORT_NAME_INSTRUMENT&SORTDIR=ASCENDING"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

_ISIN_RE = re.compile(r"([A-Z]{2}[A-Z0-9]{10})$")


def _normalize_name(name: str) -> str:
    """Normalize an index name for lookup: strip non-alphanumeric, lowercase, collapse 'and'.

    Examples: 'S&P 500' -> 'sp500', 'SandP500' -> 'sp500', 'SP500' -> 'sp500',
              'DOW JONES' -> 'dowjones', 'L-DAX' -> 'ldax'
    """
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized.replace("and", "")


def _extract_isin_from_path(path: str) -> Optional[str]:
    """Extract ISIN from the last segment of a URL path."""
    last_segment = path.rstrip("/").split("/")[-1]
    match = _ISIN_RE.search(last_segment)
    return match.group(1) if match else None


def _extract_asset_class_label(href: str) -> Optional[str]:
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
            )
        )
    return members


async def _fetch_wkn(client: httpx.AsyncClient, isin: str) -> Optional[str]:
    """Fetch the WKN for an index from its comdirect detail page."""
    url = f"{BASE_URL}/inf/indizes/{isin}"
    try:
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
    async with httpx.AsyncClient(follow_redirects=True, headers=_HEADERS, timeout=30) as client:
        response = await client.get(INDEX_LIST_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", class_="table--comparison")
        if not table:
            logger.error("Index comparison table not found on %s", INDEX_LIST_URL)
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
            candidates.append((
                link_tag.get_text(strip=True),
                f"{BASE_URL}{href}",
                isin,
                int(werte_text),
            ))

        # Fetch all WKNs in parallel
        wkns = await asyncio.gather(*[_fetch_wkn(client, isin) for _, _, isin, _ in candidates])

    result = [
        IndexInfo(name=name, wkn=wkn, member_count=member_count, link=link)
        for (name, link, _, member_count), wkn in zip(candidates, wkns)
    ]
    logger.info("Fetched %d indices from comdirect", len(result))
    return result


async def fetch_index_members(index_name: str) -> list[IndexMember]:
    """Fetch all members of a named index from comdirect, handling pagination."""
    indices = await fetch_index_list()

    match = next(
        (idx for idx in indices if _normalize_name(idx.name) == _normalize_name(index_name)),
        None,
    )
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"Index '{index_name}' not found. "
            f"Supported indices: {[i.name for i in indices]}",
        )

    isin = _extract_isin_from_path(match.link)
    if not isin:
        raise HTTPException(status_code=502, detail="Could not determine ISIN for pagination")

    logger.info(
        "Fetching members for index '%s' (expected: %d) from %s",
        match.name, match.member_count, match.link,
    )

    async with httpx.AsyncClient(follow_redirects=True, headers=_HEADERS, timeout=30) as client:
        # Fetch first page
        first_response = await client.get(match.link)
        first_response.raise_for_status()
        first_soup = BeautifulSoup(first_response.content, "html.parser")

        total_pages = _get_total_pages(first_soup)
        logger.info("Index '%s' has %d page(s)", match.name, total_pages)

        members = _parse_members_from_table(first_soup)

        if total_pages > 1:
            def page_url(offset: int) -> str:
                return (
                    f"{BASE_URL}/inf/indizes/detail/werte/standard.html"
                    f"?OFFSET={offset}&ISIN={isin}"
                    f"&SORT=SHORT_NAME_INSTRUMENT&SORTDIR=ASCENDING"
                )

            pages = await asyncio.gather(*[
                client.get(page_url(offset)) for offset in range(1, total_pages)
            ])
            for page_response in pages:
                page_response.raise_for_status()
                page_soup = BeautifulSoup(page_response.content, "html.parser")
                members.extend(_parse_members_from_table(page_soup))

    if len(members) != match.member_count:
        logger.warning(
            "Member count mismatch for '%s': expected %d from overview, fetched %d",
            match.name, match.member_count, len(members),
        )
    else:
        logger.info(
            "Member count OK for '%s': %d members", match.name, len(members)
        )

    return members
