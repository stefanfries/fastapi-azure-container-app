"""
Test script to diagnose issues with comdirect endpoints.
This script tests the history endpoint functionality to identify what has changed.
"""

import asyncio
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urlencode, urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

# Constants from the app
BASE_URL = "https://www.comdirect.de"
HISTORY_PATH = "/inf/kursdaten/historic.csv"
ASSET_CLASS_DETAILS_PATH = {
    "stock": "/inf/aktien/detail/uebersicht.html",
}


async def test_instrument_page(wkn: str = "766403", id_notation: str = "20735"):
    """Test fetching the instrument page to extract currency."""
    print(f"\n{'='*80}")
    print(f"TEST 1: Fetching instrument page for WKN {wkn}")
    print(f"{'='*80}")
    
    path = ASSET_CLASS_DETAILS_PATH["stock"]
    params = {"SEARCH_VALUE": wkn, "ID_NOTATION": id_notation}
    base_url = urljoin(BASE_URL, path)
    query_string = urlencode(params)
    url = f"{base_url}?{query_string}"
    
    print(f"URL: {url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response Length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Try to find currency
                print("\nSearching for currency meta tag...")
                currency_meta = soup.find_all("meta", itemprop="priceCurrency")
                
                if currency_meta:
                    print(f"✓ Found {len(currency_meta)} currency meta tag(s)")
                    currency = currency_meta[0].get("content")
                    print(f"  Currency: {currency}")
                else:
                    print("✗ No currency meta tag found with itemprop='priceCurrency'")
                    print("\nSearching for alternative currency indicators...")
                    
                    # Try alternative searches
                    all_metas = soup.find_all("meta", itemprop=True)
                    print(f"  Found {len(all_metas)} meta tags with itemprop:")
                    for meta in all_metas[:10]:  # Show first 10
                        print(f"    - itemprop='{meta.get('itemprop')}' content='{meta.get('content')}'")
                    
                    # Search for currency in text
                    if "EUR" in response.text:
                        print("  Found 'EUR' in page text")
                    if "USD" in response.text:
                        print("  Found 'USD' in page text")
                
                return True
            else:
                print(f"✗ Failed with status code: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"✗ Exception occurred: {type(e).__name__}: {e}")
        return False


async def test_history_csv(id_notation: str = "20735", days_back: int = 28):
    """Test fetching historical CSV data."""
    print(f"\n{'='*80}")
    print(f"TEST 2: Fetching history CSV for ID_NOTATION {id_notation}")
    print(f"{'='*80}")
    
    end = datetime.now()
    start = end - timedelta(days=days_back)
    
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
    print(f"Query Params:")
    for key, value in query_params.items():
        print(f"  {key}: {value}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, params=query_params, timeout=30.0)
            print(f"\nStatus Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response Length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print("\n--- First 500 characters of response ---")
                print(response.text[:500])
                print("--- End of preview ---\n")
                
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
                    print("\n  First few rows:")
                    print(df.head())
                    return True
                    
                except Exception as e:
                    print(f"✗ CSV parsing failed: {type(e).__name__}: {e}")
                    print("\nTrying alternative parsing...")
                    
                    # Try without skiprows
                    try:
                        csv_data = StringIO(response.text)
                        df = pd.read_csv(csv_data, delimiter=";", encoding="iso-8859-15")
                        print(f"  Parsed without skiprows - Shape: {df.shape}")
                        print(f"  Columns: {df.columns.tolist()}")
                        print("\n  First few rows:")
                        print(df.head())
                    except Exception as e2:
                        print(f"  Also failed: {type(e2).__name__}: {e2}")
                    
                    return False
            else:
                print(f"✗ Failed with status code: {response.status_code}")
                print(f"Response text: {response.text[:500]}")
                return False
                
    except Exception as e:
        print(f"✗ Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_different_instruments():
    """Test with different instruments to see if it's instrument-specific."""
    print(f"\n{'='*80}")
    print(f"TEST 3: Testing with different instruments")
    print(f"{'='*80}")
    
    test_instruments = [
        {"name": "Siemens", "wkn": "723610", "id_notation": "20666"},
        {"name": "Apple", "wkn": "865985", "id_notation": "21830"},
        {"name": "MSCI World ETF", "wkn": "A0RPWH", "id_notation": "106038350"},
    ]
    
    for instrument in test_instruments:
        print(f"\n--- Testing {instrument['name']} (WKN: {instrument['wkn']}) ---")
        
        # Quick test of history endpoint
        end = datetime.now()
        start = end - timedelta(days=7)
        url = urljoin(BASE_URL, HISTORY_PATH)
        
        query_params = {
            "DATETIME_TZ_END_RANGE": int(end.timestamp()),
            "DATETIME_TZ_END_RANGE_FORMATED": end.strftime("%d.%m.%Y"),
            "DATETIME_TZ_START_RANGE": int(start.timestamp()),
            "DATETIME_TZ_START_RANGE_FORMATED": start.strftime("%d.%m.%Y"),
            "ID_NOTATION": instrument["id_notation"],
            "INTERVALL": "16",
            "WITH_EARNINGS": False,
            "OFFSET": 0,
        }
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, params=query_params, timeout=30.0)
                status = "✓" if response.status_code == 200 else "✗"
                print(f"  {status} Status: {response.status_code}, Length: {len(response.content)} bytes")
                
                if response.status_code == 200 and len(response.content) > 0:
                    print(f"  Preview: {response.text[:100]}")
                    
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}: {e}")


async def main():
    """Run all tests."""
    print("="*80)
    print("COMDIRECT ENDPOINT DIAGNOSTIC TEST")
    print("="*80)
    print(f"Test Date: {datetime.now()}")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: Instrument page (for currency extraction)
    result1 = await test_instrument_page()
    
    # Test 2: History CSV endpoint
    result2 = await test_history_csv()
    
    # Test 3: Multiple instruments
    await test_with_different_instruments()
    
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Instrument Page Test: {'PASSED' if result1 else 'FAILED'}")
    print(f"History CSV Test: {'PASSED' if result2 else 'FAILED'}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
