# Preferred ID_NOTATION Implementation Guide

## Overview

The parser system now extracts **preferred ID_NOTATIONs** based on liquidity metrics from comdirect's trading venue tables. This ensures that the system automatically selects the most liquid trading venues for each instrument.

## How It Works

### Liquidity Metrics

Comdirect provides different liquidity indicators for different venue types:

#### Life Trading (LiveTrading) Venues
- **Metric**: "Gestellte Kurse" (Quoted Prices)
- **Meaning**: Total number of price quotes provided by the market maker
- **Higher is better**: More quotes = higher liquidity
- **Typical values**: 3,000 - 7,000 for active stocks

#### Exchange Trading (Börse) Venues
- **Metric**: "Anzahl Kurse" (Number of Quotes)
- **Meaning**: Total number of price updates during the trading day
- **Higher is better**: More updates = higher liquidity
- **Typical values**: 100 - 20,000+ depending on the exchange

### HTML Structure

The liquidity data is stored in tables:

#### Life Trading Table
```html
<table>
  <thead>
    <tr>
      <th>LiveTrading</th>
      <th>Geld</th>
      <th>Brief</th>
      <th>Datum</th>
      <th>Zeit</th>
      <th>Gestellte Kurse</th>  <!-- Liquidity column -->
    </tr>
    <tr>
      <!-- Headers with venue names and ID_NOTATIONs -->
      <th data-label="LiveTrading">
        <a data-plugin="{...ID_NOTATION=3240541...}">LT Lang & Schwarz</a>
      </th>
      <!-- More venue headers... -->
    </tr>
  </thead>
  <tbody>
    <tr>
      <td data-label="LT Lang & Schwarz">...</td>
      <td data-label="Geld">...</td>
      <td data-label="Brief">...</td>
      <td data-label="Datum">...</td>
      <td data-label="Zeit">...</td>
      <td data-label="Gestellte Kurse">6.860</td>  <!-- Liquidity value -->
    </tr>
  </tbody>
</table>
```

#### Exchange Trading Table
```html
<table>
  <thead>
    <tr>
      <th>Börse</th>
      <th>Aktuell</th>
      <th>Datum</th>
      <th>Zeit</th>
      <th>Tages.-Vol.</th>
      <th>Anzahl Kurse</th>  <!-- Liquidity column -->
    </tr>
    <tr>
      <!-- Headers with venue names and ID_NOTATIONs -->
      <th>
        <a data-plugin="{...ID_NOTATION=1929749...}">Xetra</a>
      </th>
      <!-- More venue headers... -->
    </tr>
  </thead>
  <tbody>
    <tr>
      <td data-label="Xetra">...</td>
      <td data-label="Aktuell">...</td>
      <td data-label="Datum">...</td>
      <td data-label="Zeit">...</td>
      <td data-label="Tages.-Vol.">...</td>
      <td data-label="Anzahl Kurse">18.110</td>  <!-- Liquidity value -->
    </tr>
  </tbody>
</table>
```

## Extraction Algorithm

### Step 1: Build Venue-to-ID Mapping from Headers

```python
venue_to_id = {}
for header in table.find_all("th"):
    link = header.find("a")
    if link:
        data_plugin = link.get("data-plugin", "")
        if "ID_NOTATION=" in data_plugin:
            venue_name = header.get_text(strip=True)
            id_notation = extract_id_notation_from_data_plugin(data_plugin)
            venue_to_id[venue_name] = id_notation
```

**Example Result:**
```python
{
    "LT Lang & Schwarz": "3240541",
    "LT Baader Trading": "46986389",
    "LT Societe Generale": "10336985"
}
```

### Step 2: Extract Liquidity Values from Table Rows

```python
venues_with_liquidity = []
for row in tbody.find_all("tr"):
    cells = row.find_all("td")
    
    # Get venue name from first cell's data-label
    venue_name = cells[0].get("data-label", "")
    
    # Get liquidity value
    for cell in cells:
        if cell.get("data-label") == "Gestellte Kurse":  # Or "Anzahl Kurse"
            liquidity_text = cell.get_text(strip=True)
            # Convert "6.860" to integer 6860
            liquidity_value = int(liquidity_text.replace(".", "").replace(",", ""))
            break
    
    # Match to ID_NOTATION
    id_notation = venue_to_id.get(venue_name)
    
    if venue_name and id_notation and liquidity_value:
        venues_with_liquidity.append({
            "venue": venue_name,
            "id_notation": id_notation,
            "liquidity": liquidity_value
        })
```

**Example Result:**
```python
[
    {"venue": "LT Lang & Schwarz", "id_notation": "3240541", "liquidity": 6860},
    {"venue": "LT Baader Trading", "id_notation": "46986389", "liquidity": 4946},
    {"venue": "LT Societe Generale", "id_notation": "10336985", "liquidity": 3603}
]
```

### Step 3: Select Preferred Venue (Highest Liquidity)

```python
if venues_with_liquidity:
    preferred = max(venues_with_liquidity, key=lambda x: x["liquidity"])
    return preferred["id_notation"]
```

**Result:** `"3240541"` (LT Lang & Schwarz with 6,860 Gestellte Kurse)

## Implementation in Parsers

### BaseDataParser Interface

```python
from typing import Dict, Optional, Tuple

class BaseDataParser(ABC):
    @abstractmethod
    def parse_id_notations(
        self, 
        soup: BeautifulSoup,
        default_id_notation: Optional[str] = None
    ) -> Tuple[
        Optional[Dict[str, str]],  # life_trading_dict
        Optional[Dict[str, str]],  # exchange_trading_dict
        Optional[str],              # preferred_lt_id_notation
        Optional[str]               # preferred_ex_id_notation
    ]:
        """Extract venues, IDs, and preferred IDs based on liquidity."""
        pass
```

### StockParser Implementation

```python
class StockParser(BaseDataParser):
    def parse_id_notations(self, soup, default_id_notation=None):
        # ... extract venue dictionaries ...
        
        # Extract preferred based on liquidity
        preferred_lt = self._extract_preferred_lt_notation(soup, lt_venue_dict)
        preferred_ex = self._extract_preferred_ex_notation(soup, ex_venue_dict)
        
        return lt_venue_dict, ex_venue_dict, preferred_lt, preferred_ex
    
    def _extract_preferred_lt_notation(self, soup, lt_venue_dict):
        """Find Life Trading venue with highest 'Gestellte Kurse'."""
        # Implementation details...
        
    def _extract_preferred_ex_notation(self, soup, ex_venue_dict):
        """Find Exchange Trading venue with highest 'Anzahl Kurse'."""
        # Implementation details...
```

### WarrantParser Implementation

```python
class WarrantParser(BaseDataParser):
    def parse_id_notations(self, soup, default_id_notation=None):
        # ... extract venue dictionaries ...
        
        # Warrants may have single venue - use fallback logic
        preferred_lt = self._extract_preferred_lt_notation(soup, lt_venue_dict)
        preferred_ex = self._extract_preferred_ex_notation(soup, ex_venue_dict)
        
        return lt_venue_dict, ex_venue_dict, preferred_lt, preferred_ex
    
    def _extract_preferred_lt_notation(self, soup, lt_venue_dict):
        """Extract preferred LT, fallback to first if only one venue."""
        if not lt_venue_dict:
            return None
        
        # If only one venue, it's the preferred one
        if len(lt_venue_dict) == 1:
            return list(lt_venue_dict.values())[0]
        
        # Otherwise, find venue with highest liquidity
        # ... implementation ...
```

## Usage in BaseData Model

The BaseData model exposes these fields:

```python
class BaseData(BaseModel):
    # Venue dictionaries
    id_notations_life_trading: Optional[dict[str, str]]
    id_notations_exchange_trading: Optional[dict[str, str]]
    
    # Preferred venues (based on liquidity)
    preferred_id_notation_life_trading: Optional[str]
    preferred_id_notation_exchange_trading: Optional[str]
    
    # Default venue (from URL redirect)
    default_id_notation: Optional[str]
```

### Example Usage

```python
basedata = await parse_base_data("723610")  # Siemens

print(f"Default venue: {basedata.default_id_notation}")
# Output: 9385813 (Tradegate BSX)

print(f"Preferred LT venue: {basedata.preferred_id_notation_life_trading}")
# Output: 3240541 (LT Lang & Schwarz - highest liquidity)

print(f"Preferred EX venue: {basedata.preferred_id_notation_exchange_trading}")
# Output: 1929749 (Xetra - highest liquidity)

# All available venues
print(f"All LT venues: {basedata.id_notations_life_trading}")
# Output: {"LT Lang & Schwarz": "3240541", "LT Baader Trading": "46986389", ...}

print(f"All EX venues: {basedata.id_notations_exchange_trading}")
# Output: {"Xetra": "1929749", "LS Exchange": "244494483", ...}
```

## Real-World Example: Siemens (WKN: 723610)

### Life Trading Analysis
```
Venue                       ID_NOTATION    Gestellte Kurse
────────────────────────────────────────────────────────────
LT Lang & Schwarz           3240541        6,860  ⭐ PREFERRED
LT Baader Trading           46986389       4,946
LT Societe Generale         10336985       3,603
```

**Result**: `preferred_id_notation_life_trading = "3240541"`

### Exchange Trading Analysis
```
Venue                       ID_NOTATION    Anzahl Kurse
────────────────────────────────────────────────────────────
Xetra                       1929749        18,110  ⭐ PREFERRED
LS Exchange                 244494483      8,488
Tradegate BSX               9385813        1,475
gettex                      120479869      957
Stuttgart                   21815          213
Quotrix                     134129153      116
... 11 more venues ...
```

**Result**: `preferred_id_notation_exchange_trading = "1929749"`

## Fallback Logic

### Single Venue Instruments

For instruments with only one trading venue (common for warrants):

```python
if len(lt_venue_dict) == 1:
    # Only one venue, it's automatically preferred
    return list(lt_venue_dict.values())[0]
```

### No Liquidity Data Available

If the table doesn't contain liquidity columns:

```python
# Return first venue as fallback
return list(lt_venue_dict.values())[0] if lt_venue_dict else None
```

### Error Handling

```python
try:
    liquidity_value = int(liquidity_text.replace(".", "").replace(",", ""))
except (ValueError, AttributeError):
    liquidity_value = 0  # Use 0 as fallback
```

## Testing

### Test Script: `test_preferred_notations.py`

```python
import asyncio
from app.parsers.basedata import parse_base_data

async def test():
    # Test with Siemens
    basedata = await parse_base_data("723610")
    
    # Verify preferred IDs are correct
    assert basedata.preferred_id_notation_life_trading in \
           basedata.id_notations_life_trading.values()
    
    assert basedata.preferred_id_notation_exchange_trading in \
           basedata.id_notations_exchange_trading.values()
    
    print("✓ All preferred ID_NOTATIONs validated!")

asyncio.run(test())
```

### Expected Output

```
✓ Name: Siemens
✓ WKN: 723610
✓ Default ID_NOTATION: 9385813

★★★ PREFERRED Life Trading ID_NOTATION: 3240541
★★★ PREFERRED Exchange Trading ID_NOTATION: 1929749

✓ Preferred LT ID is in Life Trading venues
✓ Preferred EX ID is in Exchange Trading venues
```

## Benefits

### 1. Automatic Best Venue Selection
- System automatically selects most liquid venue
- No manual configuration needed
- Adapts to changing market conditions

### 2. Trading Efficiency
- Higher liquidity = better execution
- Lower spreads on liquid venues
- Faster order execution

### 3. Data Quality
- Ensures data comes from most active venues
- More reliable price information
- Better historical data for analysis

### 4. Flexibility
- All venues still available if needed
- Can override with specific venue if required
- Fallback logic ensures robustness

## Troubleshooting

### Problem: preferred_id_notation is None

**Possible Causes:**
1. No liquidity table found in HTML
2. Table structure changed
3. Asset class doesn't have liquidity data

**Solution:**
- Check if table exists with `"Gestellte Kurse"` or `"Anzahl Kurse"` headers
- Verify HTML structure hasn't changed
- Use fallback to first venue in dictionary

### Problem: preferred_id_notation not in venue dictionary

**Cause:** ID_NOTATION extraction mismatch between header and row

**Solution:**
- Verify venue name matching between headers and rows
- Check for whitespace differences
- Ensure data-label attribute matches exactly

### Problem: All venues have liquidity = 0

**Cause:** Parsing error in liquidity value extraction

**Solution:**
- Check number format (periods vs commas)
- Verify cell data-label attribute
- Add more robust error handling

## Future Enhancements

### 1. Liquidity Thresholds
```python
MIN_LIQUIDITY_LT = 1000  # Minimum Gestellte Kurse
MIN_LIQUIDITY_EX = 100   # Minimum Anzahl Kurse

if liquidity_value < MIN_LIQUIDITY_LT:
    logger.warning(f"Low liquidity for {venue_name}: {liquidity_value}")
```

### 2. Historical Liquidity Tracking
- Store liquidity metrics over time
- Detect liquidity trends
- Alert on significant changes

### 3. Multiple Preferred Venues
- Return top 3 venues instead of just one
- Provide fallback options
- Enable load balancing across venues

### 4. Venue-Specific Configuration
```python
# User preferences
PREFERRED_VENUES = {
    "life_trading": ["LT Lang & Schwarz", "LT Baader Trading"],
    "exchange_trading": ["Xetra", "Frankfurt"]
}
```

## Conclusion

The preferred ID_NOTATION implementation provides:
- ✅ Automatic selection of most liquid venues
- ✅ Data-driven trading decisions
- ✅ Robust fallback logic
- ✅ Extensible architecture for future enhancements

This ensures the system always uses the best available trading venue based on objective liquidity metrics from comdirect.
