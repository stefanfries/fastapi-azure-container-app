# Plugin-Based Parser System Documentation

## Overview

The comdirect API parser has been re-engineered using a **plugin pattern with factory design**, providing a flexible and extensible architecture for parsing different asset classes.

## Problem Solved

The history endpoint was returning 500 errors for warrants because:
1. **Different HTML structures**: Warrants have a different HTML structure than stocks on comdirect
2. **Missing trading venues**: The original parser couldn't extract ID_NOTATIONs from warrant pages
3. **Chicken-and-egg problem**: Warrants require an ID_NOTATION in the URL to display complete information, but we needed to parse the page to get ID_NOTATIONS

## Architecture

### Plugin Pattern Benefits

- **Separation of concerns**: Each asset class has its own parser with specific logic
- **Easy to extend**: New asset classes can be added without modifying existing code
- **Maintainable**: Changes to one asset class don't affect others
- **Testable**: Each parser can be tested independently

### Structure

```
app/parsers/plugins/
├── __init__.py              # Package initialization
├── base_parser.py           # Abstract base class (interface)
├── stock_parser.py          # Parser for STOCK, BOND, ETF, FONDS, CERTIFICATE
├── warrant_parser.py        # Parser for WARRANT
└── factory.py               # Factory for creating parsers
```

## Key Components

### 1. BaseDataParser (Abstract Base Class)

Defines the interface that all parsers must implement:

```python
class BaseDataParser(ABC):
    @abstractmethod
    def parse_name(self, soup: BeautifulSoup) -> str
    
    @abstractmethod
    def parse_wkn(self, soup: BeautifulSoup) -> str
    
    @abstractmethod
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]
    
    @abstractmethod
    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: Optional[str]
    ) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]
    
    def needs_id_notation_refetch(self) -> bool
```

### 2. StockParser

Handles the standard HTML structure used by:
- STOCK (Aktien)
- BOND (Anleihen)
- ETF
- FONDS
- CERTIFICATE (Zertifikate)

**Key feature**: Uses `#marketSelect` dropdown or simple-table to extract trading venues.

### 3. WarrantParser

Handles the special structure for warrants (Optionsscheine):
- **Refetch mechanism**: Indicates it needs to be refetched with ID_NOTATION
- **Trading venue categorization**: Separates Life Trading (LT prefix) from Exchange Trading
- **Requires ID_NOTATION**: Cannot extract complete data without ID_NOTATION in URL

### 4. ParserFactory

Central registry and factory for creating parsers:

```python
# Register a parser
ParserFactory.register_parser(AssetClass.WARRANT, WarrantParser)

# Get a parser
parser = ParserFactory.get_parser(AssetClass.WARRANT)

# Check if registered
if ParserFactory.is_registered(asset_class):
    # use plugin
else:
    # fall back to legacy
```

## How It Works

### Normal Flow (STOCK, BOND, ETF, etc.)

1. Fetch instrument page with WKN
2. Parse asset class from URL
3. Get appropriate parser from factory
4. Parse all fields (name, WKN, ISIN, ID_NOTATIONs)
5. Return BaseData

### Special Flow (WARRANT)

1. Fetch instrument page with WKN
2. Parse asset class from URL
3. Get WarrantParser from factory
4. **Check `needs_id_notation_refetch()`** → Returns True
5. Extract default_id_notation from first response URL
6. **Refetch page WITH ID_NOTATION parameter**
7. Parse all fields from refetched page
8. Return BaseData with complete trading venue information

## Test Results

### Warrant MJ85T6 (Previously Failing)

**Before Plugin System:**
```
✗ ValueError: Invalid id_notation 489859490 for instrument MJ85T6
```

**After Plugin System:**
```
✓ Basedata parsed successfully
  Name: Morgan Stanley  Call 20.03.26 Netflix 90
  WKN: MJ85T6
  Asset Class: AssetClass.WARRANT
  Default ID_NOTATION: 489859490
  
  Life Trading Venues:
    LT Morgan Stanley: 489859490
  
  Exchange Trading Venues:
    Stuttgart: 489866209

✓ History data retrieved successfully!
  Trading Venue: LT Morgan Stanley
  Number of data points: 20
```

## Adding New Asset Classes

To add support for a new asset class (e.g., INDEX, COMMODITY, CURRENCY):

### 1. Create a new parser plugin

```python
# app/parsers/plugins/index_parser.py

from app.parsers.plugins.base_parser import BaseDataParser

class IndexParser(BaseDataParser):
    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.INDEX
    
    def parse_name(self, soup: BeautifulSoup) -> str:
        # Implement index-specific name parsing
        pass
    
    # Implement other required methods...
```

### 2. Register in factory

```python
# app/parsers/plugins/factory.py

from app.parsers.plugins.index_parser import IndexParser

ParserFactory.register_parser(AssetClass.INDEX, IndexParser)
```

### 3. Test

```python
basedata = await parse_base_data("INDEX_WKN")
# Automatically uses IndexParser
```

## Backward Compatibility

The system maintains backward compatibility:
- **Registered asset classes**: Use new plugin system
- **Unregistered asset classes**: Fall back to legacy `_parse_base_data_legacy()`
- **Gradual migration**: Can migrate asset classes one at a time

## Files Modified

### New Files Created
- `app/parsers/plugins/__init__.py`
- `app/parsers/plugins/base_parser.py`
- `app/parsers/plugins/stock_parser.py`
- `app/parsers/plugins/warrant_parser.py`
- `app/parsers/plugins/factory.py`

### Modified Files
- `app/parsers/basedata.py` - Updated `parse_base_data()` to use plugin system

### Test Files Created
- `test_plugin_system.py` - Comprehensive tests for the new system
- `test_warrant_MJ85T6.py` - Specific warrant tests
- `test_correct_id_notations.py` - ID_NOTATION validation tests

## Benefits Achieved

1. ✅ **Fixed warrant parsing** - Warrants now work correctly
2. ✅ **Extensible architecture** - Easy to add new asset classes
3. ✅ **Maintainable code** - Clear separation of concerns
4. ✅ **Backward compatible** - Existing functionality preserved
5. ✅ **Well-documented** - Clear interfaces and examples
6. ✅ **Tested** - Comprehensive test coverage

## Next Steps

### Recommended Improvements

1. **Migrate remaining asset classes** to plugin system:
   - INDEX (Indizes)
   - COMMODITY (Rohstoffe)
   - CURRENCY (Währungen)

2. **Add more parser methods** to the interface:
   - `parse_symbol()`
   - `parse_price()`
   - `parse_market_data()`

3. **Enhance error handling**:
   - Add specific exceptions for each parser
   - Better error messages with context

4. **Add caching**:
   - Cache basedata to reduce API calls
   - Especially useful for warrant refetch mechanism

5. **Add monitoring**:
   - Track which parsers are being used
   - Identify if HTML structure changes

## Usage Examples

### Basic Usage

```python
from app.parsers.basedata import parse_base_data

# Works for any registered asset class
basedata = await parse_base_data("MJ85T6")  # Warrant
basedata = await parse_base_data("766403")  # Stock
basedata = await parse_base_data("A0RPWH")  # ETF
```

### Custom Parser

```python
from app.parsers.plugins.factory import ParserFactory
from app.parsers.plugins.base_parser import BaseDataParser

class MyCustomParser(BaseDataParser):
    # Implement required methods
    pass

# Register
ParserFactory.register_parser(AssetClass.CUSTOM, MyCustomParser)
```

### Check Parser Availability

```python
if ParserFactory.is_registered(asset_class):
    parser = ParserFactory.get_parser(asset_class)
    # Use plugin system
else:
    # Fall back to legacy or show error
    pass
```

## Conclusion

The plugin-based parser system successfully resolves the warrant parsing issue while providing a scalable, maintainable architecture for future enhancements. The system is production-ready and fully tested with both stocks and warrants.
