"""Diagnostic script: fetch warrant finder pages and report row counts per OFFSET."""

import asyncio
import sys

sys.path.insert(0, ".")

import httpx
from bs4 import BeautifulSoup

URL = (
    "https://www.comdirect.de/inf/optionsscheine/selector/trefferliste.html"
    "?FORM_NAME=DerivativesSelectorOptionsscheineForm"
    "&PRESELECTION=CALL"
    "&ISSUER_ACTION=true"
    "&ISSUER_NO_FEE_ACTION=true"
    "&ID_NOTATION_UNDERLYING=9386126"
    "&UNDERLYING_TYPE=FREI"
    "&UNDERLYING_NAME_SEARCH=NVIDIA"
    "&PREDEFINED_UNDERLYING="
    "&STRIKE_ABS_FROM=200"
    "&STRIKE_ABS_TO=220"
    "&DATE_TIME_MATURITY_FROM=Range_6M"
    "&DATE_TIME_MATURITY_FROM_CAL="
    "&DATE_TIME_MATURITY_TO=Range_1Y"
    "&DATE_TIME_MATURITY_TO_CAL="
    "&ID_GROUP_ISSUER="
    "&IMPLIED_VOLATILITY_VALUE=&IMPLIED_VOLATILITY_COMPARATOR=gt"
    "&DELTA_VALUE=&DELTA_COMPARATOR=gt"
    "&LEVERAGE_VALUE=&LEVERAGE_COMPARATOR=gt"
    "&PREMIUM_PER_ANNUM_VALUE=&PREMIUM_PER_ANNUM_COMPARATOR=gt"
    "&GEARING_VALUE=&GEARING_COMPARATOR=gt"
    "&PRESENT_VALUE_VALUE=&PRESENT_VALUE_COMPARATOR=gt"
    "&SPREAD_ASK_PCT_VALUE=&SPREAD_ASK_PCT_COMPARATOR=gt"
    "&THETA_DAY_VALUE=&THETA_DAY_COMPARATOR=gt"
    "&THEORETICAL_VALUE_VALUE=&THEORETICAL_VALUE_COMPARATOR=gt"
    "&INTRINSIC_VALUE_VALUE=&INTRINSIC_VALUE_COMPARATOR=gt"
    "&BREAK_EVEN_VALUE=&BREAK_EVEN_COMPARATOR=gt"
    "&MONEYNESS_VALUE=&MONEYNESS_COMPARATOR=gt"
    "&VEGA_VALUE=&VEGA_COMPARATOR=gt"
    "&GAMMA_VALUE=&GAMMA_COMPARATOR=gt"
    "&keepCookie=true"
)


def count_isin_rows(html: bytes) -> tuple[int, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table--comparison")
    if not table:
        return 0, []
    isins = []
    for row in table.find_all("tr"):
        cell = row.find(["td", "th"], attrs={"data-label": "ISIN"})
        if cell:
            isin = cell.get_text(strip=True)
            if isin:
                isins.append(isin)
    return len(isins), isins


def get_pagination_info(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    pager = soup.find("div", class_="pagination")
    if not pager:
        return "no pagination widget"
    spans = pager.find_all("span", class_="pagination__page")
    return f"pagination spans: {[s.get_text(strip=True) for s in spans]}"


async def main() -> None:
    all_isins: set[str] = set()
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        # Page 1 (no OFFSET)
        r = await client.get(URL)
        r.raise_for_status()
        count, isins = count_isin_rows(r.content)
        pag = get_pagination_info(r.content)
        print(f"  page 1 (no OFFSET): {count} rows | {pag}")
        all_isins.update(isins)

        # Pages 2–20 with OFFSET=1, 2, ...
        for offset in range(1, 20):
            r = await client.get(f"{URL}&OFFSET={offset}")
            r.raise_for_status()
            count, isins = count_isin_rows(r.content)
            pag = get_pagination_info(r.content)
            new_isins = [i for i in isins if i not in all_isins]
            all_isins.update(new_isins)
            print(f"  OFFSET={offset}: {count} rows ({len(new_isins)} new ISINs) | {pag}")
            if count == 0:
                print("  → empty page, stopping")
                break

    print(f"\nTotal unique ISINs: {len(all_isins)}")


asyncio.run(main())
