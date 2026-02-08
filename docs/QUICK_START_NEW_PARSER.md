# Quick Start: Adding a New Asset Class Parser

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
