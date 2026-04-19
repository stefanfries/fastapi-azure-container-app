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
app/parsers/plugins/
├── __init__.py                  # Package initialization
├── base_parser.py               # Abstract base class (interface)
├── standard_asset_parser.py     # Parser for STOCK, BOND, ETF, FONDS, CERTIFICATE
├── warrant_parser.py            # Parser for WARRANT
├── special_asset_parser.py      # Parser for INDEX, COMMODITY, CURRENCY
├── parsing_utils.py             # Shared HTML extraction utilities
└── factory.py                   # Factory for creating parsers
```

## Asset Class Coverage

| Asset Class | Parser | Notes |
| ----------- | ------ | ----- |
| STOCK | `StandardAssetParser` | Full venue + id_notation support |
| BOND | `StandardAssetParser` | Full venue + id_notation support |
| ETF | `StandardAssetParser` | Full venue + id_notation support |
| FONDS | `StandardAssetParser` | Full venue + id_notation support |
| CERTIFICATE | `StandardAssetParser` | Full venue + id_notation support |
| WARRANT | `WarrantParser` | Requires id_notation in URL for full venue data |
| INDEX | `SpecialAssetParser` | No venues (non-tradeable) |
| COMMODITY | `SpecialAssetParser` | No venues (non-tradeable) |
| CURRENCY | `SpecialAssetParser` | No venues (non-tradeable) |

## Key Components

### 1. InstrumentParser (Abstract Base Class)

Defines the interface that all parsers must implement (`app/parsers/plugins/base_parser.py`):

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
```

### 2. StandardAssetParser

Handles the standard comdirect HTML structure used by STOCK, BOND, ETF, FONDS, and CERTIFICATE.

- WKN at position 1 in H2 token list (`"WKN: 918422 ISIN: ..."`)
- ISIN at position 3 in H2 token list
- Trading venues from `#marketSelect` dropdown or single-venue `.simple-table`
- Asset-class label stripped from end of H1 using `str.removesuffix()`

### 3. WarrantParser

Handles WARRANT (Optionsscheine):

- Same H1/H2 structure as standard assets
- Trading venues only available when page fetched **with** `ID_NOTATION` query parameter
- Falls back gracefully to `(None, None, None, None)` if page was fetched without `ID_NOTATION`

### 4. SpecialAssetParser

Handles INDEX, COMMODITY, and CURRENCY — instruments that are **not directly tradeable**:

- WKN at position 2 in H2 token list (different layout from standard assets)
- `parse_isin()` always returns `None`
- `parse_id_notations()` always returns `(None, None, None, None)`
- Instrument name is returned **including** the asset-class suffix (e.g. `"DAX Index"`, `"Gold Rohstoff"`)

### 5. ParserFactory

Central registry and factory (`app/parsers/plugins/factory.py`):

```python
# Get a parser instance
parser = ParserFactory.get_parser(asset_class)  # raises ValueError if unregistered

# Check registration
ParserFactory.is_registered(asset_class)  # -> bool
```

Parsers that accept `asset_class` in their constructor (`StandardAssetParser`, `SpecialAssetParser`) receive it automatically via the factory.

## Shared Utilities (parsing_utils.py)

Common HTML extraction helpers shared across all parsers:

| Function | Description |
| -------- | ----------- |
| `extract_name_from_h1` | Extracts H1 text, decomposes `<span>` children, optionally removes trailing suffix |
| `extract_wkn_from_h2` | Extracts WKN from H2 token list at a given position offset |
| `extract_after_label` | Extracts value after a label (e.g. `"ISIN:"`) in H2 |
| `extract_venues_from_dropdown` | Extracts venue→id_notation map from `#marketSelect` |
| `extract_venue_from_single_table` | Extracts single venue from `.simple-table` |
| `categorize_lt_ex_venues` | Splits venues into Life Trading / Exchange Trading dicts |
| `extract_preferred_lt_notation` | Picks LT venue with highest "Gestellte Kurse" |
| `extract_preferred_ex_notation` | Picks EX venue with highest "Anzahl Kurse" |
| `infer_currency` | Infers ISO 4217 currency from venue name |
| `clean_numeric_value` | Parses German-format numbers with magnitude suffixes |

## How It Works

### Standard Flow (STOCK, BOND, ETF, FONDS, CERTIFICATE)

1. Fetch instrument page with WKN/ISIN
2. Parse asset class from redirected URL path
3. Retrieve `StandardAssetParser(asset_class)` from factory
4. Parse name, WKN, ISIN, id_notations, preferred notations
5. Return `Instrument`

### Warrant Flow

1. Fetch instrument page — default URL only returns partial venue data
2. Parse asset class → `WarrantParser`
3. Extract `default_id_notation` from redirected URL query string
4. Parse all fields; venue data is populated when `ID_NOTATION` was present in the URL

### Special Asset Flow (INDEX, COMMODITY, CURRENCY)

1. Fetch instrument page
2. Parse asset class → `SpecialAssetParser(asset_class)`
3. Parse name (full H1 text including suffix) and WKN (H2 position 2)
4. All venue/notation fields are `None` — these instruments are not tradeable directly

## Adding a New Asset Class

See [QUICK_START_NEW_PARSER.md](QUICK_START_NEW_PARSER.md).
