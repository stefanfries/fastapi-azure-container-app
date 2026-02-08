"""
Check if Siemens page needs ID_NOTATION like warrants.
"""

import asyncio

import httpx
from bs4 import BeautifulSoup

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL
from app.models.basedata import AssetClass


async def test_siemens_with_id_notation():
    """Test if fetching with ID_NOTATION makes a difference."""
    print("="*80)
    print("TESTING SIEMENS WITH AND WITHOUT ID_NOTATION")
    print("="*80)
    
    wkn = "723610"
    id_notation = "9385813"  # From the test output
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Test 1: With only WKN
        print(f"\n1. Fetching with WKN only...")
        path = ASSET_CLASS_DETAILS_PATH[AssetClass.STOCK]
        url1 = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}"
        
        response1 = await client.get(url1, timeout=30.0)
        print(f"   Status: {response1.status_code}")
        print(f"   Final URL: {response1.url}")
        
        soup1 = BeautifulSoup(response1.content, "html.parser")
        market_select1 = soup1.select("#marketSelect")
        print(f"   #marketSelect found: {len(market_select1)}")
        
        # Test 2: With WKN and ID_NOTATION
        print(f"\n2. Fetching with WKN and ID_NOTATION...")
        url2 = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}&ID_NOTATION={id_notation}"
        
        response2 = await client.get(url2, timeout=30.0)
        print(f"   Status: {response2.status_code}")
        print(f"   Final URL: {response2.url}")
        
        soup2 = BeautifulSoup(response2.content, "html.parser")
        market_select2 = soup2.select("#marketSelect")
        print(f"   #marketSelect found: {len(market_select2)}")
        
        if market_select2:
            options = market_select2[0].find_all("option")
            print(f"   Options: {len(options)}")
            for opt in options:
                print(f"     {opt.get('value')}: {opt.get('label')}")
        
        # Test 3: With only ID_NOTATION
        print(f"\n3. Fetching with ID_NOTATION only...")
        url3 = f"{BASE_URL}{path}?ID_NOTATION={id_notation}"
        
        response3 = await client.get(url3, timeout=30.0)
        print(f"   Status: {response3.status_code}")
        print(f"   Final URL: {response3.url}")
        
        soup3 = BeautifulSoup(response3.content, "html.parser")
        market_select3 = soup3.select("#marketSelect")
        print(f"   #marketSelect found: {len(market_select3)}")
        
        if market_select3:
            options = market_select3[0].find_all("option")
            print(f"   Options: {len(options)}")
    
    print(f"\n{'='*80}")
    print("CONCLUSION:")
    print("If #marketSelect appears with ID_NOTATION but not without,")
    print("then StockParser also needs the refetch mechanism!")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_siemens_with_id_notation())
