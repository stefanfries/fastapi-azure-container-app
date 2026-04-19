# Quick Start: Adding a New Asset Class Parser

All 9 currently defined asset classes are already implemented. This guide describes how to add support for a **new** asset class should one be required in the future.

## Step-by-Step Guide

### 1. Add the Asset Class to the Enum

In `app/models/instruments.py`, add a member to `AssetClass`:

```python
class AssetClass(str, Enum):
    # existing members ...
    NEW_CLASS = ("NewClass", "GermanLabel")   # (API value, comdirect H1 suffix)
```

### 2. Add URL Mappings in constants.py

In `app/core/constants.py`, add the new class to both maps and the details path:

```python
standard_asset_classes = [..., AssetClass.NEW_CLASS]   # or special_asset_classes

asset_class_to_asset_class_identifier_map = {
    ...,
    AssetClass.NEW_CLASS: "url-path-segment",   # comdirect URL segment
}

ASSET_CLASS_DETAILS_PATH = {
    ...,
    AssetClass.NEW_CLASS: "/inf/new-class/detail/uebersicht.html",
}
```

### 3. Create a Parser

If the new class has a **standard tradeable structure** (venues, id_notations), extend `StandardAssetParser` or create a new subclass of `InstrumentParser`:

```python
# app/parsers/plugins/new_class_parser.py
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import extract_name_from_h1, extract_wkn_from_h2

class NewClassParser(InstrumentParser):
    """Parser for NEW_CLASS asset class."""

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.NEW_CLASS

    def parse_name(self, soup: BeautifulSoup) -> str:
        name = extract_name_from_h1(soup, remove_suffix=self.asset_class.comdirect_label)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name

    def parse_wkn(self, soup: BeautifulSoup) -> str:
        wkn = extract_wkn_from_h2(soup, position_offset=1)  # 1 for standard, 2 for special
        if not wkn:
            raise ValueError("Could not extract WKN from H2")
        return wkn

    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
        from app.parsers.plugins.parsing_utils import extract_after_label
        return extract_after_label(soup, "ISIN:", max_length=12)

    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, VenueInfo]], Optional[Dict[str, VenueInfo]], Optional[str], Optional[str]]:
        # Use shared utilities — see parsing_utils.py
        return None, None, None, None
```

If the new class is **non-tradeable** (like INDEX/COMMODITY/CURRENCY), simply register it with the existing `SpecialAssetParser` — no new file needed (see step 4).

### 4. Register the Parser in the Factory

In `app/parsers/plugins/factory.py`:

```python
from app.parsers.plugins.new_class_parser import NewClassParser

ParserFactory.register_parser(AssetClass.NEW_CLASS, NewClassParser)
```

Or for a non-tradeable class reusing `SpecialAssetParser`:

```python
ParserFactory.register_parser(AssetClass.NEW_CLASS, SpecialAssetParser)
```

### 5. Verify

```bash
uv run pytest tests/ -q
uv run uvicorn app.main:app --port 8080 --reload
# GET http://localhost:8080/v1/instruments/<your-test-wkn>
```


## Step-by-Step Guide

### 1. Create Your Parser File

Create `app/parsers/plugins/your_asset_parser.py`:

```python
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from app.models.basedata import AssetClass
from app.parsers.plugins.base_parser import BaseDataParser

class YourAssetParser(BaseDataParser):
    """Parser for YOUR_ASSET asset class."""
    
    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.YOUR_ASSET
    
    def parse_name(self, soup: BeautifulSoup) -> str:
        """Extract instrument name from HTML."""
        # Your implementation
        headline = soup.select_one("h1")
        return headline.text.strip() if headline else ""
    
    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """Extract WKN from HTML."""
        # Your implementation
        pass
    
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ISIN from HTML."""
        # Your implementation
        pass
    
    def parse_id_notations(
        self,
        soup: BeautifulSoup,
        default_id_notation: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
        """Extract trading venues and ID_NOTATIONs."""
        # Your implementation
        # Return: (life_trading_dict, exchange_trading_dict)
        pass
    
    def needs_id_notation_refetch(self) -> bool:
        """Override if refetch with ID_NOTATION is needed."""
        return False  # or True if needed
```

### 2. Register Your Parser

Add to `app/parsers/plugins/factory.py`:

```python
from app.parsers.plugins.your_asset_parser import YourAssetParser

# At the bottom of the file
ParserFactory.register_parser(AssetClass.YOUR_ASSET, YourAssetParser)
```

### 3. Test Your Parser

Create `test_your_asset.py`:

```python
import asyncio
from app.parsers.basedata import parse_base_data

async def test_your_asset():
    basedata = await parse_base_data("YOUR_WKN")
    print(f"Name: {basedata.name}")
    print(f"WKN: {basedata.wkn}")
    print(f"Trading Venues: {basedata.id_notations_life_trading}")

if __name__ == "__main__":
    asyncio.run(test_your_asset())
```

### 4. Run Tests

```bash
python test_your_asset.py
```

## Common Patterns

### Pattern 1: Standard Asset (like Stock)

Use `#marketSelect` dropdown:

```python
def parse_id_notations(self, soup, default_id_notation=None):
    id_notations_dict = {}
    options = soup.select("#marketSelect option")
    
    for option in options:
        label = option.get("label", "")
        value = option.get("value", "")
        if label and value:
            id_notations_dict[label] = value
    
    # Categorize into life/exchange trading
    # ...
    return lt_dict, ex_dict
```

### Pattern 2: Needs Refetch (like Warrant)

```python
def needs_id_notation_refetch(self) -> bool:
    return True

def parse_id_notations(self, soup, default_id_notation=None):
    # This will be called after refetch
    market_select = soup.select_one("#marketSelect")
    # Parse options...
```

### Pattern 3: Table-Based

```python
def parse_id_notations(self, soup, default_id_notation=None):
    tables = soup.select("table.simple-table")
    if tables:
        rows = tables[0].select("tr")
        # Extract from table rows...
```

## Debugging Tips

### 1. Save HTML for Inspection

```python
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())
```

### 2. Check Selectors

```python
print(f"Found {len(soup.select('#marketSelect'))} marketSelect elements")
print(f"Found {len(soup.find_all('table'))} tables")
```

### 3. Inspect Response URL

```python
print(f"Final URL: {response.url}")
```

## Checklist

- [ ] Created parser file in `app/parsers/plugins/`
- [ ] Implemented all required abstract methods
- [ ] Registered parser in factory
- [ ] Created test file
- [ ] Tested with real WKN
- [ ] Verified trading venues are extracted
- [ ] Checked if refetch is needed
- [ ] Added docstrings
- [ ] Updated PLUGIN_SYSTEM_DOCUMENTATION.md

## Need Help?

1. Look at existing parsers:
   - `stock_parser.py` - Standard pattern
   - `warrant_parser.py` - Refetch pattern

2. Check the base class:
   - `base_parser.py` - Interface definition

3. Review test files:
   - `test_plugin_system.py`
   - `test_warrant_MJ85T6.py`
