# Comdirect History Endpoint Diagnostic Report

**Date:** February 4, 2026  
**Issue:** History endpoint returning 500 errors

## Root Cause Analysis

### Problem
The comdirect website has changed its URL parameter requirements. It now **rejects requests** that contain both `SEARCH_VALUE` and `ID_NOTATION` parameters, returning HTTP 400 (Bad Request).

### Location of Bug
**File:** [app/parsers/history.py](app/parsers/history.py#L82)
```python
# Line 82 - This causes a 400 error
response = await fetch_one(str(basedata.wkn), basedata.asset_class, id_notation)
```

The `fetch_one` function in `app/scrapers/scrape_url.py` constructs a URL with both parameters when `id_notation` is provided, which comdirect now rejects.

## Test Results

### ✓ What Still Works
1. **CSV History Endpoint** - Working perfectly
   - URL: `https://www.comdirect.de/inf/kursdaten/historic.csv`
   - Returns data in expected format
   - Includes: instrument name, WKN, trading venue (Börse)
   
2. **HTML Pages with SEARCH_VALUE only**
   - Example: `https://www.comdirect.de/inf/aktien/detail/uebersicht.html?SEARCH_VALUE=766403`
   - Status: 200 ✓
   - Contains currency information

### ✗ What's Broken
1. **HTML Pages with both SEARCH_VALUE and ID_NOTATION**
   - Example: `https://www.comdirect.de/inf/aktien/detail/uebersicht.html?SEARCH_VALUE=766403&ID_NOTATION=20735`
   - Status: 400 ✗
   - Causes the 500 error in our API

## The Fix

**Simple Solution:** Don't pass `id_notation` when fetching the instrument page for currency extraction.

### Change Required
**File:** `app/parsers/history.py` - Line 82

**Before:**
```python
response = await fetch_one(str(basedata.wkn), basedata.asset_class, id_notation)
```

**After:**
```python
# Only pass WKN and asset_class, NOT id_notation (comdirect rejects both parameters together)
response = await fetch_one(str(basedata.wkn), basedata.asset_class, None)
```

### Why This Works
- We only need the currency from the HTML page
- Currency is the same for all notations of the same instrument
- The WKN alone is sufficient to get the instrument page
- The `id_notation` is still used correctly for the CSV history endpoint

## Additional Findings

### Data in CSV Header
The CSV first line contains:
- Instrument name
- WKN
- Trading venue (Börse)
- **Does NOT contain currency**

Example: `"DAX Performance-Index(WKN: 846900 Börse: Xetra)"`

### Currency Extraction
- Currency must still be fetched from HTML page
- Location in HTML: `<meta itemprop="priceCurrency" content="EUR">`
- This extraction logic is still valid

## Recommended Changes

### 1. Immediate Fix (Required)
Update line 82 in `app/parsers/history.py` to not pass `id_notation`

### 2. Error Handling (Recommended)
Add try-catch blocks to:
- Handle HTTP 400/404 errors gracefully
- Provide meaningful error messages
- Add fallback logic if currency extraction fails

### 3. Logging (Recommended)
Add debug logging to:
- Log the actual URL being requested
- Log HTTP status codes
- Log parsing errors

## Testing

All three test scripts have been created and verified:
1. `test_comdirect_endpoints.py` - Comprehensive endpoint testing
2. `test_url_patterns.py` - URL pattern analysis
3. `test_csv_metadata.py` - CSV header analysis

These can be run anytime to verify the fix works correctly.
