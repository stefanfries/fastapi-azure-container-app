# Plugin-Based Parser System Documentation

## Overview

The comdirect instrument parser uses a **plugin pattern with factory design**, providing a flexible and extensible architecture for parsing all supported asset classes. All 9 asset classes are fully covered by dedicated plugins — there is no legacy fallback path.

## Architecture

### Plugin Pattern Benefits

- **Separation of concerns**: Each asset class has its own parser with specific logic
- **Easy to extend**: New asset classes can be added without modifying existing code
- **Maintainable**: Changes to one asset class don't affect others
- **Testable**: Each parser can be tested independently

### Structure

```text
app/parsers/
├── base_parser.py               # InstrumentParser — abstract base class (interface)
├── standard_asset_parser.py     # StandardAssetParser — shared abstract base for tradeable assets
├── special_asset_parser.py      # SpecialAssetParser — INDEX, COMMODITY, CURRENCY
└── plugins/
    ├── __init__.py                  # Package initialization
    ├── stock_parser.py              # StockParser — STOCK
    ├── bond_parser.py               # BondParser — BOND
    ├── etf_parser.py                # ETFParser — ETF
    ├── fonds_parser.py              # FondsParser — FONDS
    ├── certificate_parser.py        # CertificateParser — CERTIFICATE
    ├── warrant_parser.py            # WarrantParser — WARRANT
    ├── parsing_utils.py             # Shared HTML extraction utilities
    └── factory.py                   # Factory for creating parsers
```

## Asset Class Coverage

| Asset Class | Parser | `parse_details()` | Notes |
| ----------- | ------ | ----------------- | ----- |
| STOCK | `StockParser` | ✅ `StockDetails` | Full venue + id_notation support |
| BOND | `BondParser` | ✅ `BondDetails` | Full venue + id_notation support |
| ETF | `ETFParser` | ✅ `ETFDetails` | Full venue + id_notation support |
| FONDS | `FondsParser` | ✅ `FondsDetails` | Full venue + id_notation support |
| CERTIFICATE | `CertificateParser` | ✅ `CertificateDetails` | Full venue + id_notation support |
| WARRANT | `WarrantParser` | ✅ `WarrantDetails` | Requires id_notation in URL for full venue data |
| INDEX | `SpecialAssetParser` | ✅ `IndexDetails` | No venues (non-tradeable); `constituents_url` links to `/v1/indices/{isin}` |
| COMMODITY | `SpecialAssetParser` | ✅ `CommodityDetails` | No venues (non-tradeable) |
| CURRENCY | `SpecialAssetParser` | ✅ `CurrencyDetails` | No venues (non-tradeable) |

## Key Components

### 1. InstrumentParser (Abstract Base Class)

Defines the interface that all parsers must implement (`app/parsers/base_parser.py`):

```python
class InstrumentParser(ABC):
    @property
    @abstractmethod
    def asset_class(self) -> AssetClass: ...

    @abstractmethod
    def parse_name(self, soup: BeautifulSoup) -> str: ...

    @abstractmethod
    def parse_wkn(self, soup: BeautifulSoup) -> str: ...

    @abstractmethod
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]: ...

    @abstractmethod
    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: Optional[str]
    ) -> Tuple[Optional[Dict], Optional[Dict], Optional[str], Optional[str]]: ...

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        """Default: return None. Override in subclasses."""
        return None
```

The non-abstract `parse_details()` default lets parsers not yet extended remain fully valid — the `Instrument.details` field will be `None` until the subclass implements it.

### 2. StandardAssetParser

Handles the standard comdirect HTML structure used by STOCK, BOND, ETF, FONDS, and CERTIFICATE.

- WKN at position 1 in H2 token list (`"WKN: 918422 ISIN: ..."`)
- ISIN at position 3 in H2 token list
- Trading venues from `#marketSelect` dropdown or single-venue `.simple-table`
- Asset-class label stripped from end of H1 using `str.removesuffix()`
- **`parse_details()`** dispatches by `asset_class` to a dedicated private method:
  - `_parse_stock_details()` — reads "Aktieninformationen"; extracts `Branche` from `<span title>`; handles market cap magnitude suffixes `Bil.` (10¹²), `Mrd.` (10⁹), `Mio.` (10⁶)
  - `_parse_bond_details()` — reads "Anleiheinformationen"; extracts coupon rate, maturity date, credit ratings
  - `_parse_etf_details()` — reads "ETF-Informationen"; extracts tracked index, TER, replication method, fund size
  - `_parse_fonds_details()` — reads "Fondsinformationen"; extracts fund manager, distribution policy, fund size
  - `_parse_certificate_details()` — reads "Zertifikatinformationen"; extracts certificate type, cap, barrier, participation rate
  - Returns `None` for unregistered classes (INDEX, COMMODITY, CURRENCY) handled by `SpecialAssetParser`
  - Shared static helpers: `_parse_date(text)` → `date | None` (DD.MM.YYYY / DD.MM.YY); `_split_value_currency(raw)` → `tuple[float|None, str|None]`

### 3. WarrantParser

Handles WARRANT (Optionsscheine):

- Same H1/H2 structure as standard assets
- Trading venues only available when page fetched **with** `ID_NOTATION` query parameter
- Falls back gracefully to `(None, None, None, None)` if page was fetched without `ID_NOTATION`
- **`parse_details()`** always returns a `WarrantDetails` instance from the "Stammdaten" table:
  - `Typ`: reconstructs full text using `<span title>` — "Call (Amerikanisch)" instead of "Call (Amer.)"
  - `Basiswert`: `underlying_name` from `<span title>`, `underlying_link` built from `<a href>`
  - `Emittent`: issuer name from the visible `<td>` display text (`get_text()`), not the `<a title>` attribute
  - All fields fall back to `None` for `"--"` or `"k. A."` placeholders

### 4. SpecialAssetParser

Handles INDEX, COMMODITY, and CURRENCY — instruments that are **not directly tradeable**:

- WKN at position 2 in H2 token list (different layout from standard assets)
- `parse_wkn()` returns `None` (not raises) for instruments where WKN is `"--"` (e.g. L&S Brent Oil)
- `parse_isin()` reads ISIN from the Stammdaten table `"ISIN"` row; returns `None` if absent or `"--"`
- `parse_id_notations()` always returns `(None, None, None, None)`
- Instrument name is returned **including** the asset-class suffix (e.g. `"DAX Index"`, `"Gold Rohstoff"`)
- **`parse_details()`** dispatches by `asset_class`:
  - `_parse_index_details()` — reads Stammdaten: `Land` → `country`, `Landeswährung` → `currency`, `Enthaltene Werte` → `num_constituents` (int); `ISIN` or `WKN` row → `constituents_url` (e.g. `/v1/indices/DE0008469008`)
  - `_parse_commodity_details()` — reads `Landeswährung` → `currency`, `Symbol` → `symbol`, `Land` → `country`
  - `_parse_currency_details()` — reads `Wechselkurs` (e.g. `"EUR/USD"`) split on `"/"` → `base_currency` / `quote_currency`; `Land` → `country`

### 5. ParserFactory

Central registry and factory (`app/parsers/plugins/factory.py`):

```python
# Get a parser instance
parser = ParserFactory.get_parser(asset_class)  # raises ValueError if unregistered

# Check registration
ParserFactory.is_registered(asset_class)  # -> bool
```

Only `SpecialAssetParser` accepts `asset_class` in its constructor — it receives it automatically via the factory.

## Shared Utilities (parsing_utils.py)

Common HTML extraction helpers shared across all parsers:

| Function | Description |
| -------- | ----------- |
| `extract_name_from_h1` | Extracts H1 text, decomposes `<span>` children, optionally removes trailing suffix |
| `extract_wkn_from_h2` | Extracts WKN from H2 token list at a given position offset |
| `extract_after_label` | Extracts value after a label (e.g. `"ISIN:"`) in H2 |
| `extract_venues_from_dropdown` | Extracts venue→id_notation map from `#marketSelect` |
| `extract_venue_from_single_table` | Extracts single venue from `.simple-table` |
| `extract_table_cell_by_label` | Extracts a `<td>` value by finding a matching `<th>` under a named section |
| `categorize_lt_ex_venues` | Splits venues into Life Trading / Exchange Trading dicts |
| `extract_preferred_lt_notation` | Picks LT venue with highest "Gestellte Kurse" |
| `extract_preferred_ex_notation` | Picks EX venue with highest "Anzahl Kurse" |
| `infer_currency` | Infers ISO 4217 currency from venue name |
| `clean_numeric_value` | Parses German-format numbers with magnitude suffixes (`Tsd.`, `Mio.`, `Mrd.`, `Bil.`) |
| `clean_float_value` | Parses German decimal strings (`"2,34 %"` → `2.34`, `"--"` → `None`) |

## How It Works

### Standard Flow (STOCK, BOND, ETF, FONDS, CERTIFICATE)

1. Fetch instrument page with WKN/ISIN
2. Parse asset class from redirected URL path
3. Retrieve the concrete parser (e.g. `StockParser()`) from factory
4. Parse name, WKN, ISIN, id_notations, preferred notations
5. Call `parse_details(soup)` — returns the asset-class-specific `Details` model
6. Return `Instrument` with optional `details`

### Warrant Flow

1. Fetch instrument page — default URL only returns partial venue data
2. Parse asset class → `WarrantParser`
3. Extract `default_id_notation` from redirected URL query string
4. Parse all fields; venue data is populated when `ID_NOTATION` was present in the URL
5. Call `parse_details(soup)` — returns `WarrantDetails` with full names from span/a attributes

### Special Asset Flow (INDEX, COMMODITY, CURRENCY)

1. Fetch instrument page
2. Parse asset class → `SpecialAssetParser(asset_class)`
3. Parse name (full H1 text including suffix), WKN (H2 position 2, or `None` if `"--"`), ISIN (Stammdaten table)
4. All venue/notation fields are `None` — these instruments are not tradeable directly
5. `parse_details()` returns `IndexDetails`, `CommodityDetails`, or `CurrencyDetails` as appropriate

## Asset-Class-Specific Detail Models

All models live in `app/models/instrument_details.py` as a Pydantic v2 discriminated union:

```python
InstrumentDetails = Annotated[
    StockDetails | BondDetails | ETFDetails | FondsDetails | WarrantDetails
    | CertificateDetails | IndexDetails | CommodityDetails | CurrencyDetails,
    Field(discriminator="asset_class")
]
```

Each model carries the static "Stammdaten" fields for its asset class. The `Instrument` model exposes them via an optional field:

```python
class Instrument(BaseModel):
    ...
    details: InstrumentDetails | None = None
```

FastAPI serialises the correct concrete model based on the `asset_class` literal — no manual type-switching needed.

### IndexDetails fields

| Field | Source label | Type | Notes |
| ----- | ------------ | ---- | ----- |
| `country` | `Land` | `str \| None` | Country of the index |
| `currency` | `Landeswährung` | `str \| None` | e.g. `"EUR"` |
| `num_constituents` | `Enthaltene Werte` | `int \| None` | Number of index members |
| `constituents_url` | `ISIN` / `WKN` | `str \| None` | e.g. `/v1/indices/DE0008469008` |

### CommodityDetails fields

| Field | Source label | Type |
| ----- | ------------ | ---- |
| `currency` | `Landeswährung` | `str \| None` |
| `symbol` | `Symbol` | `str \| None` |
| `country` | `Land` | `str \| None` |

### CurrencyDetails fields

| Field | Source label | Type |
| ----- | ------------ | ---- |
| `base_currency` | `Wechselkurs` (before `/`) | `str \| None` |
| `quote_currency` | `Wechselkurs` (after `/`) | `str \| None` |
| `country` | `Land` | `str \| None` |

## Adding a New Asset Class

See [QUICK_START_NEW_PARSER.md](QUICK_START_NEW_PARSER.md).

---

## Warrant Finder (`app/parsers/warrants.py`)

This module is **separate from the `WarrantParser` plugin** above.  `WarrantParser` parses a
single warrant's instrument detail page; `app/parsers/warrants.py` drives the comdirect
Optionsschein Finder (screener) and returns a list of matching warrants.

### Key functions

| Function | Description |
| --- | --- |
| `build_warrant_finder_url(...)` | Assembles the comdirect `trefferliste.html` URL from all filter params |
| `fetch_warrants(...)` | Resolves underlying WKN/ISIN → id_notation, builds URL, fetches all pages concurrently, deduplicates results |
| `_greek_filter_pairs(prefix, min_val, max_val)` | Builds `(VALUE, COMPARATOR)` pairs for one Greek dimension |
| `_parse_warrant_rows(soup)` | Extracts `Warrant` objects from one results page |
| `_parse_maturity_param(value)` | Converts Range_* codes or date strings to comdirect maturity params |

### Greek / analytics filter encoding

Comdirect encodes dual bounds as **repeated query parameters** (Strategy C):

```text
DELTA_VALUE=0.5&DELTA_COMPARATOR=gt&DELTA_VALUE=0.8&DELTA_COMPARATOR=lt
```

`_greek_filter_pairs()` builds this list.  When both bounds are `None` the filter is emitted
disabled (empty value + `gt`) to satisfy comdirect's required parameter structure.

Supported comparators: `gt` (greater than), `lt` (less than).
The `eq` (equal) comparator was tested and rejected — it returns 0 results for every tested
continuous analytics value because comdirect applies exact float matching server-side.

### All 14 exposed filter dimensions

| API params | Comdirect prefix |
| --- | --- |
| `delta_min`, `delta_max` | `DELTA` |
| `omega_min`, `omega_max` | `GEARING` |
| `moneyness_min`, `moneyness_max` | `MONEYNESS` |
| `premium_per_annum_min`, `premium_per_annum_max` | `PREMIUM_PER_ANNUM` |
| `implied_volatility_min`, `implied_volatility_max` | `IMPLIED_VOLATILITY` |
| `leverage_min`, `leverage_max` | `LEVERAGE` |
| `spread_ask_pct_min`, `spread_ask_pct_max` | `SPREAD_ASK_PCT` |
| `theta_day_min`, `theta_day_max` | `THETA_DAY` |
| `present_value_min`, `present_value_max` | `PRESENT_VALUE` |
| `theoretical_value_min`, `theoretical_value_max` | `THEORETICAL_VALUE` |
| `intrinsic_value_min`, `intrinsic_value_max` | `INTRINSIC_VALUE` |
| `break_even_min`, `break_even_max` | `BREAK_EVEN` |
| `vega_min`, `vega_max` | `VEGA` |
| `gamma_min`, `gamma_max` | `GAMMA` |

### Sentinel value caveat

Comdirect assigns a sentinel value ≥ 1.0 to warrants that have no published analytics data
(certain issuers do not submit real-time Greeks to comdirect).  A `gt 0.5` filter passes these
warrants (1.0 > 0.5), but a subsequent `lt 0.9` upper bound blocks them (1.0 ≥ 0.9).  This can
make Greek range filters appear to return fewer results than a single lower-bound filter.

Combining `issuer_action=true` or `issuer_no_fee_action=true` with upper-bound Greek filters is
therefore discouraged — both query param descriptions carry an explicit warning about this.
