"""
Compare issuer_action warrant set vs regular set, then fetch analytics
for warrants that appear exclusively in each set.

Run with:
    uv run python scripts/compare_action_sets.py
"""

import asyncio

import httpx

BASE = "http://localhost:8080"
PARAMS = "underlying=US67066G1040&preselection=CALL&strike_min=200&strike_max=200&maturity_from=Range_6M&maturity_to=Range_1Y"


async def fetch_isins(client: httpx.AsyncClient, extra: str = "") -> set[str]:
    url = f"{BASE}/v1/warrants/?{PARAMS}{extra}"
    r = await client.get(url)
    r.raise_for_status()
    return {w["isin"] for w in r.json()["results"]}


async def fetch_analytics(client: httpx.AsyncClient, isin: str) -> dict:
    r = await client.get(f"{BASE}/v1/warrants/{isin}")
    if r.status_code != 200:
        return {}
    body = r.json()
    a = body.get("analytics", {})
    m = body.get("market_data", {})
    return {"delta": a.get("delta"), "bid": m.get("bid"), "ask": m.get("ask")}


async def run() -> None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        action = await fetch_isins(client, "&issuer_action=true&issuer_no_fee_action=true")
        regular = await fetch_isins(client)

    print(f"issuer_action set : {len(action):>3} warrants")
    print(f"regular set       : {len(regular):>3} warrants")
    print()

    only_action = sorted(action - regular)
    only_regular = sorted(regular - action)
    in_both = sorted(action & regular)

    print(f"Only in action set ({len(only_action)}): {only_action}")
    print(f"Only in regular    ({len(only_regular)}): {only_regular}")
    print(f"In both            ({len(in_both)}): {in_both}")
    print()

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        for label, isins in [
            ("ONLY in issuer_action set", only_action),
            ("In BOTH sets", in_both),
        ]:
            if not isins:
                continue
            print(f"--- {label} ---")
            for isin in isins:
                info = await fetch_analytics(client, isin)
                delta = str(info.get("delta"))
                bid = str(info.get("bid"))
                ask = str(info.get("ask"))
                print(f"  {isin}  delta={delta:>6}  bid={bid:>7}  ask={ask:>7}")
            print()


if __name__ == "__main__":
    asyncio.run(run())
