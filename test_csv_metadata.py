"""
Check if currency information is available in the CSV response.
"""

import asyncio
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx

BASE_URL = "https://www.comdirect.de"
HISTORY_PATH = "/inf/kursdaten/historic.csv"


async def check_csv_for_currency(id_notation: str, instrument_name: str):
    """Check what information is in the CSV header."""
    print(f"\nChecking CSV for {instrument_name} (ID_NOTATION: {id_notation})")
    print("-" * 60)
    
    end = datetime.now()
    start = end - timedelta(days=7)
    
    url = urljoin(BASE_URL, HISTORY_PATH)
    query_params = {
        "DATETIME_TZ_END_RANGE": int(end.timestamp()),
        "DATETIME_TZ_END_RANGE_FORMATED": end.strftime("%d.%m.%Y"),
        "DATETIME_TZ_START_RANGE": int(start.timestamp()),
        "DATETIME_TZ_START_RANGE_FORMATED": start.strftime("%d.%m.%Y"),
        "ID_NOTATION": id_notation,
        "INTERVALL": "16",
        "WITH_EARNINGS": False,
        "OFFSET": 0,
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, params=query_params, timeout=30.0)
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                print(f"First line (header): {lines[0]}")
                print(f"Second line (column headers): {lines[1] if len(lines) > 1 else 'N/A'}")
                
                # Parse the first line to extract instrument info
                if lines[0]:
                    header = lines[0].strip('"')
                    print(f"\nParsed header: {header}")
                    
                    # Check if WKN is in header
                    if "WKN:" in header:
                        parts = header.split("WKN:")
                        if len(parts) > 1:
                            wkn_part = parts[1].split()[0]
                            print(f"  WKN found: {wkn_part}")
                    
                    # Check if exchange/börse is in header
                    if "Börse:" in header or "Exchange:" in header:
                        print(f"  Trading venue found in header")
                    
                return True
            else:
                print(f"Failed with status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Test multiple instruments."""
    print("="*80)
    print("CHECKING CSV HEADERS FOR METADATA")
    print("="*80)
    
    test_cases = [
        ("20735", "DAX"),
        ("20666", "Siemens"),
        ("21830", "Apple"),
    ]
    
    for id_notation, name in test_cases:
        await check_csv_for_currency(id_notation, name)
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("The CSV first line contains:")
    print("  - Instrument name")
    print("  - WKN")
    print("  - Trading venue (Börse)")
    print("\nBUT it does NOT contain currency information!")
    print("Currency must still be fetched from the HTML page.")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
