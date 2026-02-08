"""
Test with CORRECT WKN and ID_NOTATION pairs using the actual basedata parser.
"""

import asyncio
from urllib.parse import urlencode, urljoin

import httpx

from app.parsers.basedata import parse_base_data

BASE_URL = "https://www.comdirect.de"


async def test_with_correct_pairs():
    """Test with actual matching WKN and ID_NOTATION pairs from basedata."""
    print("="*80)
    print("TESTING WITH CORRECT WKN AND ID_NOTATION PAIRS")
    print("="*80)
    
    test_instruments = [
        ("766403", "DAX"),
        ("723610", "Siemens"),
        ("865985", "Apple"),
    ]
    
    for wkn, name in test_instruments:
        print(f"\n{'='*80}")
        print(f"Testing: {name} (WKN: {wkn})")
        print(f"{'='*80}")
        
        try:
            # Get the actual basedata including correct ID_NOTATION
            basedata = await parse_base_data(wkn)
            
            print(f"Instrument: {basedata.name}")
            print(f"WKN: {basedata.wkn}")
            print(f"Asset Class: {basedata.asset_class}")
            print(f"Default ID_NOTATION: {basedata.default_id_notation}")
            
            # Test with matching WKN and ID_NOTATION
            # Map asset class to correct path
            from app.core.constants import ASSET_CLASS_DETAILS_PATH
            path = ASSET_CLASS_DETAILS_PATH.get(basedata.asset_class)
            url_with_both = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}&ID_NOTATION={basedata.default_id_notation}"
            url_wkn_only = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}"
            url_notation_only = f"{BASE_URL}{path}?ID_NOTATION={basedata.default_id_notation}"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Test 1: Both parameters (with CORRECT matching values)
                print(f"\nTest 1: Both SEARCH_VALUE and ID_NOTATION")
                print(f"  URL: {url_with_both}")
                try:
                    response = await client.get(url_with_both, timeout=30.0)
                    status_symbol = "✓" if response.status_code == 200 else "✗"
                    print(f"  {status_symbol} Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        if "priceCurrency" in response.text:
                            print(f"  ✓ Contains currency metadata")
                except Exception as e:
                    print(f"  ✗ Exception: {type(e).__name__}: {e}")
                
                # Test 2: WKN only
                print(f"\nTest 2: SEARCH_VALUE only")
                print(f"  URL: {url_wkn_only}")
                try:
                    response = await client.get(url_wkn_only, timeout=30.0)
                    status_symbol = "✓" if response.status_code == 200 else "✗"
                    print(f"  {status_symbol} Status: {response.status_code}")
                except Exception as e:
                    print(f"  ✗ Exception: {type(e).__name__}: {e}")
                
                # Test 3: ID_NOTATION only
                print(f"\nTest 3: ID_NOTATION only")
                print(f"  URL: {url_notation_only}")
                try:
                    response = await client.get(url_notation_only, timeout=30.0)
                    status_symbol = "✓" if response.status_code == 200 else "✗"
                    print(f"  {status_symbol} Status: {response.status_code}")
                except Exception as e:
                    print(f"  ✗ Exception: {type(e).__name__}: {e}")
                    
        except Exception as e:
            print(f"✗ Error parsing basedata: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_with_correct_pairs())
