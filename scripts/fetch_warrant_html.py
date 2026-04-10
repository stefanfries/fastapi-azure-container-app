"""
Fetch the warrant finder results page and save HTML for structure analysis.

Run with:
    uv run python -m scripts.fetch_warrant_html
"""

import asyncio

import httpx

from app.models.warrants import WarrantPreselection
from app.parsers.warrants import build_warrant_finder_url

OUTPUT_FILE = "scripts/warrant_finder_response.html"


async def main():
    url = build_warrant_finder_url(
        id_notation_underlying="277381",
        underlying_name="NVIDIA CORPORATION",
        preselection=WarrantPreselection.CALL,
        issuer_action=False,
        issuer_no_fee_action=False,
        strike_min=100.0,
        strike_max=200.0,
        maturity_from="Range_6M",
        maturity_to="Range_1Y",
    )
    print(f"Fetching: {url}\n")

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(url)

    print(f"Status : {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Size   : {len(response.content):,} bytes")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Saved  : {OUTPUT_FILE}")


asyncio.run(main())
