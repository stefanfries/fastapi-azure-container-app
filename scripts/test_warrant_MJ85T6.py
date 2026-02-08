"""
Test the specific failing warrant: MJ85T6
"""

import asyncio
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL, HISTORY_PATH
from app.parsers.basedata import parse_base_data


async def test_warrant_basedata():
    """Test fetching basedata for the warrant."""
    print("="*80)
    print("TEST 1: Fetching basedata for warrant MJ85T6")
    print("="*80)
    
    wkn = "MJ85T6"
    
    try:
        basedata = await parse_base_data(wkn)
        print(f"✓ Basedata parsed successfully")
        print(f"  Name: {basedata.name}")
        print(f"  WKN: {basedata.wkn}")
        print(f"  Asset Class: {basedata.asset_class}")
        print(f"  Default ID_NOTATION: {basedata.default_id_notation}")
        
        return basedata
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_warrant_html_page(wkn, id_notation, asset_class):
    """Test fetching HTML page for currency extraction."""
    print(f"\n{'='*80}")
    print(f"TEST 2: Fetching HTML page for currency (WKN: {wkn}, ID_NOTATION: {id_notation})")
    print(f"{'='*80}")
    
    path = ASSET_CLASS_DETAILS_PATH.get(asset_class)
    url = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}&ID_NOTATION={id_notation}"
    
    print(f"URL: {url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ HTML page loaded successfully")
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Try to find currency
                print("\nSearching for currency meta tag...")
                currency_meta = soup.find_all("meta", itemprop="priceCurrency")
                
                if currency_meta:
                    currency = currency_meta[0].get("content")
                    print(f"✓ Found currency: {currency}")
                    return currency
                else:
                    print(f"✗ No currency meta tag found!")
                    print("\nSearching for alternative currency indicators...")
                    
                    # Look for all meta tags
                    all_metas = soup.find_all("meta", itemprop=True)
                    print(f"Found {len(all_metas)} meta tags with itemprop:")
                    for meta in all_metas[:10]:
                        print(f"  - itemprop='{meta.get('itemprop')}' content='{meta.get('content')}'")
                    
                    return None
            else:
                print(f"✗ Failed with status: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_warrant_history_csv(id_notation):
    """Test fetching history CSV."""
    print(f"\n{'='*80}")
    print(f"TEST 3: Fetching history CSV (ID_NOTATION: {id_notation})")
    print(f"{'='*80}")
    
    end = datetime.now()
    start = end - timedelta(days=14)
    
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    url = urljoin(BASE_URL, HISTORY_PATH)
    
    query_params = {
        "DATETIME_TZ_END_RANGE": int(end.timestamp()),
        "DATETIME_TZ_END_RANGE_FORMATED": end.strftime("%d.%m.%Y"),
        "DATETIME_TZ_START_RANGE": int(start.timestamp()),
        "DATETIME_TZ_START_RANGE_FORMATED": start.strftime("%d.%m.%Y"),
        "ID_NOTATION": id_notation,
        "INTERVALL": "16",  # daily
        "WITH_EARNINGS": False,
        "OFFSET": 0,
    }
    
    print(f"URL: {url}")
    print(f"Date range: {start.strftime('%d.%m.%Y')} to {end.strftime('%d.%m.%Y')}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, params=query_params, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response Length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print(f"\n--- First 500 characters of response ---")
                print(response.text[:500])
                print(f"--- End of preview ---\n")
                
                # Try to parse as CSV
                print("Attempting to parse as CSV...")
                try:
                    csv_data = StringIO(response.text)
                    df = pd.read_csv(
                        csv_data,
                        skiprows=2,
                        delimiter=";",
                        quotechar='"',
                        encoding="iso-8859-15",
                    )
                    print(f"✓ CSV parsed successfully!")
                    print(f"  Shape: {df.shape}")
                    print(f"  Columns: {df.columns.tolist()}")
                    if len(df) > 0:
                        print(f"\n  First few rows:")
                        print(df.head())
                    else:
                        print(f"  ⚠ DataFrame is empty!")
                    return True
                    
                except Exception as e:
                    print(f"✗ CSV parsing failed: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"✗ Failed with status: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_history_flow():
    """Test the complete flow as it happens in parse_history_data."""
    print(f"\n{'='*80}")
    print(f"TEST 4: Complete history flow simulation")
    print(f"{'='*80}")
    
    wkn = "MJ85T6"
    
    try:
        # Step 1: Get basedata
        from app.parsers.history import parse_history_data
        
        # Call the actual parse_history_data function
        history_data = await parse_history_data(
            instrument_id=wkn,
            start=None,
            end=None,
            interval="day",
            id_notation=None,  # Use default
        )
        
        print(f"✓ History data retrieved successfully!")
        print(f"  WKN: {history_data.wkn}")
        print(f"  Name: {history_data.name}")
        print(f"  Currency: {history_data.currency}")
        print(f"  Trading Venue: {history_data.trading_venue}")
        print(f"  Number of data points: {len(history_data.data)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in history flow: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests for the warrant."""
    print("="*80)
    print("TESTING WARRANT MJ85T6")
    print("="*80)
    
    # Test 1: Basedata
    basedata = await test_warrant_basedata()
    
    if basedata:
        # Test 2: HTML page for currency
        currency = await test_warrant_html_page(
            basedata.wkn,
            basedata.default_id_notation,
            basedata.asset_class
        )
        
        # Test 3: History CSV
        await test_warrant_history_csv(basedata.default_id_notation)
    
    # Test 4: Full flow
    await test_full_history_flow()
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
