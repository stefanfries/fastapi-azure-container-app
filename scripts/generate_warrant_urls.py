"""
Generate warrant finder URLs for manual browser testing.

Each scenario prints a labelled URL you can open directly in your browser.

Run with:
    uv run python scripts/generate_warrant_urls.py
"""

from app.models.warrants import WarrantPreselection
from app.parsers.warrants import build_warrant_finder_url

# id_notation values for common underlyings:
#   NVIDIA CORPORATION  → 9386126  (WKN: 918422, Tradegate, default_id_notation)
#   Apple Inc.          → 27482 (example — adjust if needed)
#   DAX (index)         → 20735 (example — adjust if needed)

SCENARIOS = [
    {
        "label": "NVIDIA — all warrants, no filters",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
        ),
    },
    {
        "label": "NVIDIA — CALL only, maturity 6M–1Y",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.CALL,
            maturity_from="Range_6M",
            maturity_to="Range_1Y",
        ),
    },
    {
        "label": "NVIDIA — PUT only, maturity 3M–2Y",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.PUT,
            maturity_from="Range_3M",
            maturity_to="Range_2Y",
        ),
    },
    {
        "label": "NVIDIA — CALL, strike 100–150, any (unexpired) maturity",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.CALL,
            strike_min=100.0,
            strike_max=150.0,
            # No maturity_from: leave empty to show all unexpired warrants.
            # Range_* codes are forward-looking upper bounds and are not valid
            # as a FROM value — using Range_NOW as FROM causes comdirect to
            # ignore the form submission entirely.
        ),
    },
    {
        "label": "NVIDIA — CALL, no-fee warrants only, explicit date range",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.CALL,
            issuer_no_fee_action=True,
            maturity_from="2026-06-01",
            maturity_to="2027-12-31",
        ),
    },
    {
        "label": "NVIDIA — flat-fee (Aktion) + no-fee, CALL, strike 200",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.CALL,
            issuer_action=True,
            issuer_no_fee_action=True,
            strike_min=200.0,
            strike_max=200.0,
            maturity_from="Range_6M",
            maturity_to="Range_1Y",
        ),
    },
    {
        "label": "NVIDIA — comdirect date format (DD.MM.YYYY)",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.CALL,
            maturity_from="01.01.2027",
            maturity_to="30.10.2027",
        ),
    },
    {
        "label": "NVIDIA — PUT, no maturity filter (open-ended)",
        "kwargs": dict(
            id_notation_underlying="9386126",
            underlying_name="NVIDIA CORPORATION",
            preselection=WarrantPreselection.PUT,
        ),
    },
]


def main() -> None:
    for i, scenario in enumerate(SCENARIOS, start=1):
        url = build_warrant_finder_url(**scenario["kwargs"])
        print(f"\n{'─' * 70}")
        print(f"[{i}] {scenario['label']}")
        print(f"{'─' * 70}")
        print(url)

    print(f"\n{'─' * 70}")
    print(f"Generated {len(SCENARIOS)} URLs.")


if __name__ == "__main__":
    main()
