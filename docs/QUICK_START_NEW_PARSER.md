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

### 3. Add a Detail Model

In `app/models/instrument_details.py`, add a new Pydantic model and register it in the union:

```python
class NewClassDetails(BaseModel):
    asset_class: Literal["NewClass"] = "NewClass"
    # add your fields here, all optional
    some_field: str | None = Field(None, description="...")

# Add to the union at the bottom of the file:
InstrumentDetails = Annotated[
    StockDetails | ... | NewClassDetails,
    Field(discriminator="asset_class")
]
```

### 4. Create a Parser

If the new class has a **standard tradeable structure** (venues, id_notations), extend `StandardAssetParser` or create a new subclass of `InstrumentParser`:

```python
# app/parsers/plugins/new_class_parser.py
from bs4 import BeautifulSoup
from app.models.instrument_details import InstrumentDetails, NewClassDetails
from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import (
    extract_name_from_h1,
    extract_wkn_from_h2,
    extract_after_label,
)

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

    def parse_isin(self, soup: BeautifulSoup) -> str | None:
        return extract_after_label(soup, "ISIN:", max_length=12)

    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: str | None = None
    ) -> tuple[dict[str, VenueInfo] | None, ...]:
        # Use shared utilities — see parsing_utils.py
        return None, None, None, None

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        return NewClassDetails(
            some_field=...,
        )
```

If the new class is **non-tradeable** (like INDEX/COMMODITY/CURRENCY), simply register it with the existing `SpecialAssetParser` — no new file needed (see step 5).

### 5. Register the Parser in the Factory

In `app/parsers/plugins/factory.py`:

```python
from app.parsers.plugins.new_class_parser import NewClassParser

ParserFactory.register_parser(AssetClass.NEW_CLASS, NewClassParser)
```

Or for a non-tradeable class reusing `SpecialAssetParser`:

```python
ParserFactory.register_parser(AssetClass.NEW_CLASS, SpecialAssetParser)
```

### 6. Write Tests

Create `tests/unit/test_new_class_details_parser.py`. Mirror the structure of
`tests/unit/test_warrant_details_parser.py`:

- Write a `_new_class_page()` helper that builds minimal BeautifulSoup HTML
  matching the real comdirect Stammdaten table structure for that asset class
- Test each field individually (happy path)
- Test `"--"` and `"k. A."` placeholders → `None`
- Test the no-section fallback

### 7. Verify

```bash
uv run pytest tests/ -q
uv run uvicorn app.main:app --port 8080 --reload
# GET http://localhost:8080/v1/instruments/<your-test-wkn>
```

## Discovering Real HTML Structure

Before writing the parser, fetch a real page to inspect the HTML:

```python
# scripts/debug_<new_class>.py
import asyncio
from app.parsers.instruments import parse_instrument_data
from app.models.instruments import AssetClass
from app.scrapers.scrape_url import fetch_one
from bs4 import BeautifulSoup
import re

async def main():
    inst = await parse_instrument_data("YOUR_WKN")
    resp = await fetch_one("YOUR_WKN", AssetClass.NEW_CLASS, inst.default_id_notation)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Print all rows of the relevant section table
    h2 = soup.find("h2", string=re.compile("Stammdaten"))
    if h2:
        for tr in h2.parent.find("table").find_all("tr"):
            print(repr(str(tr)))

asyncio.run(main())
```

Key things to check:
- Are values in plain `<td>` text, or inside `<span title>` / `<a title>` / `<a href>`?
- Do abbreviated display texts need to be replaced with the `title` attribute?
- Are numeric values in German format (`"1.234,56"`) or with magnitude suffixes (`"4,20 Bil.")?

## Common Extraction Patterns

| HTML pattern | Extraction |
| ------------ | ---------- |
| `<td>plain text</td>` | `extract_table_cell_by_label(soup, section, label)` |
| `<td><span title="Full Name">Abbr..</span></td>` | Read `span["title"]` |
| `<td><a href="/path" title="Full Name">Short</a></td>` | Read `a["title"]` for name, `a["href"]` for link |
| `"1.234,56 USD"` | `clean_float_value()` + split currency suffix |
| `"4,20 Bil. EUR"` | `clean_numeric_value()` + split currency suffix |
| `"DD.MM.YY"` or `"DD.MM.YYYY"` | `datetime.strptime()` with both formats |

## Checklist

- [ ] `AssetClass` enum member added
- [ ] URL mappings in `constants.py` updated
- [ ] `NewClassDetails` model created and added to `InstrumentDetails` union
- [ ] Parser file created with all abstract methods implemented
- [ ] `parse_details()` implemented and returning the new model
- [ ] Parser registered in `ParserFactory`
- [ ] Tests written (happy path + None cases + no-section fallback)
- [ ] All tests pass (`uv run pytest tests/ -q`)
- [ ] Verified live with a real WKN
- [ ] `PLUGIN_SYSTEM_DOCUMENTATION.md` asset class table updated

