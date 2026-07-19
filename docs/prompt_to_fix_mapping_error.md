# Prompt

## Status

Implemented on 2026-07-19.

## Implementation Summary

1. Canonical mapping fixes delivered:
   - `US74743L1008` -> `BG`
   - `CH0044328745` -> `CB`
   - `CH0114405324` -> `GRMN`
2. Deterministic source-priority/ranking rules added for yfinance symbol selection.
3. Auditable ISIN-keyed server-side override table added (`owner`, `reason`, `updated_at`).
4. Post-mapping Yahoo chart availability validation added with fallback promotion.
5. Index constituent data hygiene added:
   - known alias normalization by ISIN
   - duplicate checks/deduplication by ISIN
   - anomaly logging by normalized company name and override drift
6. Backfill script delivered: `scripts/backfill_mapping_overrides.py`.
7. Regression tests added and full suite passing (`609 passed`, coverage `91.06%`).
8. API response schema unchanged.

You are working on FinHub API data quality for index constituent and instrument mapping.

Goal
Fix and harden ISIN -> Yahoo symbol mapping quality in FinHub so downstream clients can rely on `global_identifiers.symbol_yfinance` without local overrides.

Context

- Client pipeline resolves S&P 500 constituents from FinHub index endpoint and then calls `/v1/instruments/{isin}`.
- Some ISINs currently map to incorrect Yahoo symbols (wrong venue suffix or stale symbol), causing missing OHLCV/fundamentals in yfinance.
- Client had to add temporary local overrides and fallback logic; this should be eliminated upstream.

Known examples to fix

1) ISIN US74743L1008 (Bunge Global S.A.) should map to Yahoo symbol `BG` (NYSE).
   - Current bad symbols observed: `Q23`, `Q23.SW`
2) ISIN CH0044328745 (Chubb) should map to `CB`
3) ISIN CH0114405324 (Garmin) should map to `GRMN`

Observed index-quality issue

- S&P 500 constituent payload includes suspicious naming for US74743L1008 ("QNITY ELECTRONICS O.N.") and duplicate-like Bunge representations.
- Please validate and correct constituent metadata normalization as part of this change.

Required FinHub changes

1. Canonical mapping:
   - Ensure `/v1/instruments/{isin}` returns correct `global_identifiers.symbol_yfinance` for problematic ISINs.
2. Mapping strategy:
   - Define deterministic source-priority/ranking rules for symbol selection (avoid wrong exchange suffixes).
3. Data hygiene:
   - Validate index constituent names for obvious anomalies and inconsistent aliases.
   - Add duplicate/anomaly checks (by ISIN and normalized company name) in ingestion pipeline.
4. Exception handling:
   - Add server-side “known overrides” table keyed by ISIN for exceptional cases.
   - Make overrides auditable (owner, reason, timestamp).
5. Validation:
   - Add automated post-mapping validation against Yahoo chart availability (symbol has recent price series).
6. Observability:
   - Add metrics/logging for mapping corrections, unresolved ISINs, and fallback usage.
7. Backward compatibility:
   - Keep API response schema unchanged.

Acceptance criteria

1. `/v1/instruments/US74743L1008` => `symbol_yfinance = "BG"`
2. `/v1/instruments/CH0044328745` => `symbol_yfinance = "CB"`
3. `/v1/instruments/CH0114405324` => `symbol_yfinance = "GRMN"`
4. No regressions for already-correct mappings.
5. S&P 500 constituent metadata no longer shows obvious malformed aliases for these entities.
6. Test suite includes regression tests for these ISINs and passes in CI.

Deliverables

1. Implementation plan with mapping rule hierarchy
2. Code diff / PR
3. Regression tests added
4. Any data backfill/migration scripts
5. Rollout + rollback plan
6. Monitoring dashboard/query examples for mapping health
