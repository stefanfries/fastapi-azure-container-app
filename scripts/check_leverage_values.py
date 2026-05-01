"""
Investigate why LEVERAGE gt 3 AND LEVERAGE lt 8 returns 23 results (= baseline).

Hypothesis A: all warrants genuinely have leverage in 3–8.
Hypothesis B: sentinel-value issue — warrants without analytics pass gt 3 but
              ALSO pass lt 8, i.e. the sentinel is < 8 (unlike delta sentinel ≥ 1.0).

Approach:
  1. Fetch the full baseline list via GET /v1/warrants/?underlying=A2PWMJ&preselection=CALL
     (maturity Range_6M to Range_2Y to match the probe script).
  2. For each warrant call GET /v1/warrants/{wkn} to get analytics.leverage.
  3. Print a table of all leverage values.

Run with the local server active:
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
    uv run python scripts/check_leverage_values.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

import httpx

API_BASE = "http://localhost:8080"
# Include X-API-Key and a browser-like User-Agent so comdirect's scraping
# guard does not block the downstream warrant-detail requests.
HEADERS = {
    "X-API-Key": "dev",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


async def main() -> None:
    async with httpx.AsyncClient(base_url=API_BASE, headers=HEADERS, timeout=60) as client:
        # Step 1: fetch baseline warrant list
        print("Fetching baseline warrants (NVIDIA CALL, maturity 6M–2Y) …")
        resp = await client.get(
            "/v1/warrants/",
            params={
                "underlying": "A2PWMJ",
                "preselection": "CALL",
                "maturity_from": "Range_6M",
                "maturity_to": "Range_2Y",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        warrants = data["results"]
        print(f"  → {len(warrants)} warrants returned\n")

        # Step 2: fetch analytics for each warrant
        print(f"{'WKN':<12} {'ISIN':<15} {'leverage':>10} {'omega':>8}  note")
        print("-" * 65)

        no_analytics = 0
        in_range = 0
        out_of_range = 0

        tasks = []
        for w in warrants:
            identifier = w.get("wkn") or w.get("isin")
            tasks.append((identifier, w.get("wkn", ""), w.get("isin", "")))

        async def fetch_detail(identifier: str) -> dict:
            r = await client.get(f"/v1/warrants/{identifier}")
            r.raise_for_status()
            return r.json()

        results = await asyncio.gather(
            *[fetch_detail(ident) for ident, _, _ in tasks], return_exceptions=True
        )

        for (identifier, wkn, isin), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"  {wkn:<12} {isin:<15} {'ERROR':>10}            {result}")
                continue

            analytics = result.get("analytics") or {}
            leverage = analytics.get("leverage")
            omega = analytics.get("omega")

            if leverage is None:
                note = "← no analytics"
                no_analytics += 1
            elif 3 < leverage < 8:
                note = "← in range"
                in_range += 1
            else:
                note = "← OUT OF RANGE"
                out_of_range += 1

            lev_str = f"{leverage:.2f}" if leverage is not None else "None"
            om_str  = f"{omega:.2f}"    if omega    is not None else "None"
            print(f"  {wkn:<12} {isin:<15} {lev_str:>10} {om_str:>8}  {note}")

        print()
        print(f"Summary: {len(warrants)} total | in range 3–8: {in_range} | "
              f"no analytics: {no_analytics} | out of range: {out_of_range}")

        if no_analytics > 0:
            print()
            print("Hypothesis B confirmed: warrants without analytics are NOT filtered")
            print("out by lt 8 — their sentinel value for LEVERAGE must be < 8.")
        elif out_of_range == 0:
            print()
            print("Hypothesis A confirmed: all warrants genuinely have leverage in 3–8.")
        else:
            print()
            print(f"{out_of_range} warrant(s) have leverage outside 3–8 yet pass the filter.")
            print("Comdirect's server-side filter may not match the scraped analytics values.")


if __name__ == "__main__":
    asyncio.run(main())
