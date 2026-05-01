"""
Explore how comdirect handles dual-bound Greek filters (min + max for one Greek).

The UI shows two rows per Greek (e.g. Delta > X  AND  Delta < Y).  The question
is how those two rows map to URL query parameters.  HTML forms with two inputs of
the same name emit repeated parameters, e.g.:

    DELTA_VALUE=0.6&DELTA_COMPARATOR=gt&DELTA_VALUE=0.75&DELTA_COMPARATOR=lt

This script tests three candidate strategies and prints result counts so you can
verify which actually filters:

  Strategy A — single lower bound only       (delta > 0.5)
  Strategy B — single upper bound only       (delta < 0.8)
  Strategy C — repeated params for range     (delta > 0.5 AND delta < 0.8)
  Strategy D — _VALUE_2 / _COMPARATOR_2 keys (hypothetical, less common)

Run with:
    uv run python scripts/test_greek_range_filters.py

Open the printed URLs in a browser to visually verify.
"""

import asyncio
import sys
from urllib.parse import urlencode

sys.path.insert(0, ".")

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.comdirect.de"
RESULTS_URL = f"{BASE_URL}/inf/optionsscheine/selector/trefferliste.html"

# NVIDIA (id_notation 9386126), CALL, maturity 6M–2Y — broad enough to get
# a decent number of results so filtering effects are visible.
BASE_PARAMS: list[tuple[str, str]] = [
    ("FORM_NAME", "DerivativesSelectorOptionsscheineForm"),
    ("PRESELECTION", "CALL"),
    ("ISSUER_ACTION", "false"),
    ("ISSUER_NO_FEE_ACTION", "false"),
    ("ID_NOTATION_UNDERLYING", "9386126"),
    ("UNDERLYING_TYPE", "FREI"),
    ("UNDERLYING_NAME_SEARCH", "NVIDIA CORPORATION"),
    ("PREDEFINED_UNDERLYING", ""),
    ("STRIKE_ABS_FROM", ""),
    ("STRIKE_ABS_TO", ""),
    ("DATE_TIME_MATURITY_FROM", "Range_6M"),
    ("DATE_TIME_MATURITY_FROM_CAL", ""),
    ("DATE_TIME_MATURITY_TO", "Range_2Y"),
    ("DATE_TIME_MATURITY_TO_CAL", ""),
    ("ID_GROUP_ISSUER", ""),
]

# Greek filler for all params not under test (empty = disabled)
GREEK_FILLER: list[tuple[str, str]] = [
    ("IMPLIED_VOLATILITY_VALUE", ""),
    ("IMPLIED_VOLATILITY_COMPARATOR", "gt"),
    ("LEVERAGE_VALUE", ""),
    ("LEVERAGE_COMPARATOR", "gt"),
    ("PREMIUM_PER_ANNUM_VALUE", ""),
    ("PREMIUM_PER_ANNUM_COMPARATOR", "gt"),
    ("GEARING_VALUE", ""),
    ("GEARING_COMPARATOR", "gt"),
    ("PRESENT_VALUE_VALUE", ""),
    ("PRESENT_VALUE_COMPARATOR", "gt"),
    ("SPREAD_ASK_PCT_VALUE", ""),
    ("SPREAD_ASK_PCT_COMPARATOR", "gt"),
    ("THETA_DAY_VALUE", ""),
    ("THETA_DAY_COMPARATOR", "gt"),
    ("THEORETICAL_VALUE_VALUE", ""),
    ("THEORETICAL_VALUE_COMPARATOR", "gt"),
    ("INTRINSIC_VALUE_VALUE", ""),
    ("INTRINSIC_VALUE_COMPARATOR", "gt"),
    ("BREAK_EVEN_VALUE", ""),
    ("BREAK_EVEN_COMPARATOR", "gt"),
    ("MONEYNESS_VALUE", ""),
    ("MONEYNESS_COMPARATOR", "gt"),
    ("VEGA_VALUE", ""),
    ("VEGA_COMPARATOR", "gt"),
    ("GAMMA_VALUE", ""),
    ("GAMMA_COMPARATOR", "gt"),
    ("keepCookie", "true"),
]


def build_url(extra_params: list[tuple[str, str]]) -> str:
    params = BASE_PARAMS + extra_params + GREEK_FILLER
    return f"{RESULTS_URL}?{urlencode(params)}"


SCENARIOS: list[dict] = [
    {
        "label": "Baseline — no Delta filter",
        "delta_params": [],
    },
    {
        "label": "Strategy A — single lower bound: Delta > 0.50",
        "delta_params": [
            ("DELTA_VALUE", "0.5"),
            ("DELTA_COMPARATOR", "gt"),
        ],
    },
    {
        "label": "Strategy B — single upper bound: Delta < 0.80",
        "delta_params": [
            ("DELTA_VALUE", "0.8"),
            ("DELTA_COMPARATOR", "lt"),
        ],
    },
    {
        "label": "Strategy C — repeated params range: Delta > 0.50 AND Delta < 0.80",
        "delta_params": [
            ("DELTA_VALUE", "0.5"),
            ("DELTA_COMPARATOR", "gt"),
            ("DELTA_VALUE", "0.8"),
            ("DELTA_COMPARATOR", "lt"),
        ],
    },
    {
        "label": "Strategy D — _VALUE_2 / _COMPARATOR_2: Delta > 0.50 AND Delta_2 < 0.80",
        "delta_params": [
            ("DELTA_VALUE", "0.5"),
            ("DELTA_COMPARATOR", "gt"),
            ("DELTA_VALUE_2", "0.8"),
            ("DELTA_COMPARATOR_2", "lt"),
        ],
    },
]


def count_rows(html: bytes) -> int:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table--comparison")
    if not table:
        return 0
    return sum(
        1
        for row in table.find_all("tr")
        if row.find(["td", "th"], attrs={"data-label": "ISIN"})
        and row.find(["td", "th"], attrs={"data-label": "ISIN"}).get_text(strip=True)
    )


async def run() -> None:
    print("=" * 72)
    print("Comdirect Greek range-filter exploration (Delta as test subject)")
    print("=" * 72)
    print()

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        for scenario in SCENARIOS:
            params = scenario["delta_params"]
            url = build_url(params)

            print(f"--- {scenario['label']} ---")
            print(f"URL:\n  {url}\n")

            try:
                resp = await client.get(url)
                resp.raise_for_status()
                n = count_rows(resp.content)
                print(f"Rows on page 1: {n}")
            except Exception as exc:
                print(f"ERROR: {exc}")

            print()


if __name__ == "__main__":
    asyncio.run(run())
