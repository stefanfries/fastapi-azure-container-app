"""
Test different URL patterns to find what works with comdirect.
"""

import asyncio
from urllib.parse import urlencode, urljoin

import httpx

BASE_URL = "https://www.comdirect.de"


async def test_url_pattern(description: str, url: str):
    """Test a specific URL pattern."""
    print(f"\n{description}")
    print(f"  URL: {url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30.0)
            status_symbol = "✓" if response.status_code == 200 else "✗"
            print(f"  {status_symbol} Status: {response.status_code}")
            print(f"  Length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                # Check for currency in response
                if "EUR" in response.text:
                    print(f"  ✓ Found 'EUR' in response")
                if "priceCurrency" in response.text:
                    print(f"  ✓ Found 'priceCurrency' in response")
                    
            return response.status_code == 200
            
    except Exception as e:
        print(f"  ✗ Exception: {type(e).__name__}: {e}")
        return False


async def main():
    """Test various URL patterns."""
    print("="*80)
    print("TESTING DIFFERENT URL PATTERNS")
    print("="*80)
    
    wkn = "766403"  # DAX
    id_notation = "20735"
    
    # Pattern 1: Original with both SEARCH_VALUE and ID_NOTATION
    url1 = f"{BASE_URL}/inf/aktien/detail/uebersicht.html?SEARCH_VALUE={wkn}&ID_NOTATION={id_notation}"
    await test_url_pattern("Pattern 1: Original (SEARCH_VALUE + ID_NOTATION)", url1)
    
    # Pattern 2: Just SEARCH_VALUE
    url2 = f"{BASE_URL}/inf/aktien/detail/uebersicht.html?SEARCH_VALUE={wkn}"
    await test_url_pattern("Pattern 2: Just SEARCH_VALUE", url2)
    
    # Pattern 3: Just ID_NOTATION
    url3 = f"{BASE_URL}/inf/aktien/detail/uebersicht.html?ID_NOTATION={id_notation}"
    await test_url_pattern("Pattern 3: Just ID_NOTATION", url3)
    
    # Pattern 4: Index page
    url4 = f"{BASE_URL}/inf/indizes/detail/uebersicht.html?ID_NOTATION={id_notation}"
    await test_url_pattern("Pattern 4: Index page with ID_NOTATION", url4)
    
    # Pattern 5: Index page with SEARCH_VALUE
    url5 = f"{BASE_URL}/inf/indizes/detail/uebersicht.html?SEARCH_VALUE={wkn}"
    await test_url_pattern("Pattern 5: Index page with SEARCH_VALUE", url5)
    
    # Pattern 6: Search page
    url6 = f"{BASE_URL}/inf/search/all.html?SEARCH_VALUE={wkn}"
    await test_url_pattern("Pattern 6: Search page", url6)
    
    # Pattern 7: Try with headers
    print(f"\nPattern 7: With User-Agent header")
    print(f"  URL: {url1}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url1, headers=headers, timeout=30.0)
            status_symbol = "✓" if response.status_code == 200 else "✗"
            print(f"  {status_symbol} Status: {response.status_code}")
            print(f"  Length: {len(response.content)} bytes")
    except Exception as e:
        print(f"  ✗ Exception: {type(e).__name__}: {e}")
    
    # Pattern 8: Try alternate stock
    print(f"\nPattern 8: Testing with different stock (Apple)")
    apple_wkn = "865985"
    url8 = f"{BASE_URL}/inf/aktien/detail/uebersicht.html?SEARCH_VALUE={apple_wkn}"
    await test_url_pattern("Apple stock page", url8)
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
