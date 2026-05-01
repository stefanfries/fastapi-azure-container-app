"""Fetch analytics for a sample of warrants to inspect actual delta values."""

import asyncio

import httpx

ISINS = [
    "DE000MG7C2H8", "DE000MJ85M66", "DE000MM0CNZ5", "DE000SY286W0",
    "DE000PL1HGS9", "DE000PL1LKS3", "DE000FA55UL3", "DE000PJ4R3A4",
    "DE000MM230P2", "DE000FA8M8U2", "DE000PJ91TP1", "DE000PK18AQ0",
    "DE000PK8F549", "DE000PK8F6S7", "DE000MN6EWS3", "DE000MN71Z38",
    "DE000PM09LG3", "DE000PM09PW1",
]


async def run() -> None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        for isin in ISINS:
            r = await client.get(f"http://localhost:8080/v1/warrants/{isin}")
            if r.status_code != 200:
                print(f"{isin}: HTTP {r.status_code}")
                continue
            body = r.json()
            a = body.get("analytics", {})
            m = body.get("market_data", {})
            delta = a.get("delta")
            omega = a.get("omega")
            iv = a.get("implied_volatility")
            bid = m.get("bid")
            ask = m.get("ask")
            print(
                f"{isin}  delta={str(delta):>6}  omega={str(omega):>8}  "
                f"iv={str(iv):>6}  bid={str(bid):>7}  ask={str(ask):>7}"
            )


if __name__ == "__main__":
    asyncio.run(run())
