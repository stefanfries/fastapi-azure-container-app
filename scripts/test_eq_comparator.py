"""
Probe whether comdirect's ``eq`` (equal) comparator for Greek filters is useful.

For continuous analytics values (delta, implied volatility, etc.) an exact-equal
filter is unlikely to return results because floating-point analytics values
virtually never match a hard-coded constant.

The key questions this script answers:

1. Does ``eq`` work at all (does it send a valid request)?
2. Does it return 0 results for all realistic values (confirming it's not useful)?
3. Are there any Greek dimensions where ``eq`` might be meaningful
   (e.g. integer-like values)?

Test matrix (all using NVIDIA CALL, maturity 6M–2Y as baseline):

  T0  Baseline                           — no Greek filter
  T1  DELTA eq 0.6                       — typical ATM delta, almost certainly 0 results
  T2  DELTA eq 0.0                       — extreme: should give 0 results
  T3  DELTA gt 0.5 AND DELTA lt 0.8     — known-good range for comparison
  T4  MONEYNESS eq 100                   — exactly ATM; might return some
  T5  MONEYNESS eq 100 (repeated param)  — verify eq works with repeated keys too
  T6  IMPLIED_VOLATILITY eq 50           — 50% IV: near-zero chance of exact match

Run with:
    uv run python scripts/test_eq_comparator.py

Open printed URLs in a browser for visual verification.

NOTE: comdirect will rate-limit or return empty results after many quick requests.
Wait a few minutes between runs, or run this script at most once per session.
"""

import asyncio
import sys
from urllib.parse import urlencode

sys.path.insert(0, ".")

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.comdirect.de"
RESULTS_URL = f"{BASE_URL}/inf/optionsscheine/selector/trefferliste.html"

# NVIDIA CALL, maturity 6M–2Y
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

# All-disabled Greek filler
ALL_DISABLED: list[tuple[str, str]] = [
    ("IMPLIED_VOLATILITY_VALUE", ""), ("IMPLIED_VOLATILITY_COMPARATOR", "gt"),
    ("DELTA_VALUE", ""),             ("DELTA_COMPARATOR", "gt"),
    ("LEVERAGE_VALUE", ""),          ("LEVERAGE_COMPARATOR", "gt"),
    ("PREMIUM_PER_ANNUM_VALUE", ""), ("PREMIUM_PER_ANNUM_COMPARATOR", "gt"),
    ("GEARING_VALUE", ""),           ("GEARING_COMPARATOR", "gt"),
    ("PRESENT_VALUE_VALUE", ""),     ("PRESENT_VALUE_COMPARATOR", "gt"),
    ("SPREAD_ASK_PCT_VALUE", ""),    ("SPREAD_ASK_PCT_COMPARATOR", "gt"),
    ("THETA_DAY_VALUE", ""),         ("THETA_DAY_COMPARATOR", "gt"),
    ("THEORETICAL_VALUE_VALUE", ""), ("THEORETICAL_VALUE_COMPARATOR", "gt"),
    ("INTRINSIC_VALUE_VALUE", ""),   ("INTRINSIC_VALUE_COMPARATOR", "gt"),
    ("BREAK_EVEN_VALUE", ""),        ("BREAK_EVEN_COMPARATOR", "gt"),
    ("MONEYNESS_VALUE", ""),         ("MONEYNESS_COMPARATOR", "gt"),
    ("VEGA_VALUE", ""),              ("VEGA_COMPARATOR", "gt"),
    ("GAMMA_VALUE", ""),             ("GAMMA_COMPARATOR", "gt"),
    ("keepCookie", "true"),
]


def _replace_greek(base: list[tuple[str, str]], overrides: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Replace ALL_DISABLED Greek params with the given overrides.

    Removes any existing key from *base* that appears in *overrides*, then
    appends *overrides* (preserving keepCookie at the end).
    """
    override_keys = {k for k, _ in overrides if k != "keepCookie"}
    filtered = [(k, v) for k, v in base if k not in override_keys and k != "keepCookie"]
    return filtered + overrides + [("keepCookie", "true")]


def count_results(soup: BeautifulSoup) -> int:
    """Extract warrant count from the results page header."""
    # Try the count badge first
    badge = soup.find(class_="badge--count")
    if badge:
        text = badge.get_text(strip=True).replace(".", "").replace(",", "")
        try:
            return int(text)
        except ValueError:
            pass
    # Fall back to counting table rows
    table = soup.find("table", class_="table--comparison")
    if not table:
        return 0
    isin_cells = table.find_all(attrs={"data-label": "ISIN"})
    return len(isin_cells)


async def fetch_count(client: httpx.AsyncClient, label: str, params: list[tuple[str, str]]) -> None:
    url = f"{RESULTS_URL}?{urlencode(params)}"
    resp = await client.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    n = count_results(soup)
    print(f"  {label:<55} → {n:>4} results")
    print(f"    URL: {url[:120]}{'...' if len(url) > 120 else ''}")
    print()


async def main() -> None:
    print("=" * 70)
    print("Comdirect 'eq' comparator probe — NVIDIA CALL 6M–2Y maturity")
    print("=" * 70)
    print()

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:

        # T0: Baseline — no filter
        t0_params = BASE_PARAMS + ALL_DISABLED
        await fetch_count(client, "T0  Baseline (no Greek filter)", t0_params)

        # T1: DELTA eq 0.6
        t1_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("DELTA_VALUE", "0.6"), ("DELTA_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T1  DELTA eq 0.6", t1_params)

        # T2: DELTA eq 0.0
        t2_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("DELTA_VALUE", "0.0"), ("DELTA_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T2  DELTA eq 0.0", t2_params)

        # T3: DELTA gt 0.5 AND DELTA lt 0.8  (known-good range)
        t3_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("DELTA_VALUE", "0.5"), ("DELTA_COMPARATOR", "gt"),
            ("DELTA_VALUE", "0.8"), ("DELTA_COMPARATOR", "lt"),
        ])
        await fetch_count(client, "T3  DELTA gt 0.5 AND DELTA lt 0.8 (range)", t3_params)

        # T4: MONEYNESS eq 100 (exactly ATM)
        t4_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("MONEYNESS_VALUE", "100"), ("MONEYNESS_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T4  MONEYNESS eq 100 (exactly ATM)", t4_params)

        # T5: MONEYNESS eq 100 via repeated param (same key twice)
        t5_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("MONEYNESS_VALUE", "100"), ("MONEYNESS_COMPARATOR", "eq"),
            ("MONEYNESS_VALUE", "100"), ("MONEYNESS_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T5  MONEYNESS eq 100 (repeated eq param)", t5_params)

        # T6: IMPLIED_VOLATILITY eq 50
        t6_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("IMPLIED_VOLATILITY_VALUE", "50"), ("IMPLIED_VOLATILITY_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T6  IMPLIED_VOLATILITY eq 50", t6_params)

        # T7: MONEYNESS gt 95 AND MONEYNESS lt 105  (range for comparison)
        t7_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("MONEYNESS_VALUE", "95"),  ("MONEYNESS_COMPARATOR", "gt"),
            ("MONEYNESS_VALUE", "105"), ("MONEYNESS_COMPARATOR", "lt"),
        ])
        await fetch_count(client, "T7  MONEYNESS gt 95 AND MONEYNESS lt 105 (range)", t7_params)

        # T8: LEVERAGE eq 5 (leverage is often more integer-like)
        t8_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("LEVERAGE_VALUE", "5"), ("LEVERAGE_COMPARATOR", "eq"),
        ])
        await fetch_count(client, "T8  LEVERAGE eq 5", t8_params)

        # T9: LEVERAGE gt 3 AND LEVERAGE lt 8  (range for comparison)
        t9_params = _replace_greek(BASE_PARAMS + ALL_DISABLED, [
            ("LEVERAGE_VALUE", "3"), ("LEVERAGE_COMPARATOR", "gt"),
            ("LEVERAGE_VALUE", "8"), ("LEVERAGE_COMPARATOR", "lt"),
        ])
        await fetch_count(client, "T9  LEVERAGE gt 3 AND LEVERAGE lt 8 (range)", t9_params)

    print("=" * 70)
    print("Interpretation guide:")
    print("  - T1/T2/T6/T8 returning 0 → eq does exact float match (useless)")
    print("  - T1/T4/T8 returning similar to T3/T7/T9 → eq behaves like gt/lt (investigate)")
    print("  - T4/T5 differ → repeated eq params have side effects")
    print("  Compare T3 vs baseline (T0) to confirm range filters work at all.")


if __name__ == "__main__":
    asyncio.run(main())
