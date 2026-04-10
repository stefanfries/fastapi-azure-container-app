"""
Compare warrant finder URLs across all available id_notations for NVIDIA.

Fetches NVIDIA instrument data to discover every exchange/LT venue it is listed
on, then generates one CALL warrant finder URL per venue so you can open each
link in the browser and compare the result counts.

The hypothesis is that the warrant finder returns the same results regardless of
which European venue's id_notation is used, since warrants are written on the
underlying company — not on a specific exchange listing.

Run with:
    $env:PYTHONPATH = "."; python scripts/compare_nvidia_notation_urls.py
"""

import asyncio

from app.models.warrants import WarrantPreselection
from app.parsers.instruments import parse_instrument_data
from app.parsers.warrants import build_warrant_finder_url

NVIDIA_WKN = "918422"

# Common maturity / type filter used across all comparison URLs so differences
# are solely due to the id_notation.
COMMON_KWARGS = dict(
    preselection=WarrantPreselection.CALL,
    maturity_from="Range_6M",
    maturity_to="Range_1Y",
)


async def main() -> None:
    print(f"Resolving NVIDIA ({NVIDIA_WKN}) instrument data …")
    instrument = await parse_instrument_data(NVIDIA_WKN)

    print(f"\nName:                {instrument.name}")
    print(f"WKN:                 {instrument.wkn}")
    print(f"ISIN:                {instrument.isin}")
    print(f"default_id_notation: {instrument.default_id_notation}")

    # Merge LT and EX venue dicts into one {venue_label: id_notation} mapping.
    all_venues: dict[str, str] = {}
    if instrument.id_notations_life_trading:
        for venue, notation in instrument.id_notations_life_trading.items():
            all_venues[f"LT — {venue}"] = notation
    if instrument.id_notations_exchange_trading:
        for venue, notation in instrument.id_notations_exchange_trading.items():
            all_venues[f"EX — {venue}"] = notation

    if not all_venues:
        print("\nNo venue id_notations found — cannot generate comparison URLs.")
        return

    print(f"\nFound {len(all_venues)} venues. Generating comparison URLs …")
    print(f"Filter: CALL, maturity 6M–1Y (same for all)\n")

    for venue_label, notation in all_venues.items():
        is_default = " ← default_id_notation" if notation == instrument.default_id_notation else ""
        url = build_warrant_finder_url(
            id_notation_underlying=notation,
            underlying_name=instrument.name,
            **COMMON_KWARGS,
        )
        print(f"{'─' * 70}")
        print(f"{venue_label}  (id_notation={notation}){is_default}")
        print(f"{'─' * 70}")
        print(url)
        print()


if __name__ == "__main__":
    asyncio.run(main())
