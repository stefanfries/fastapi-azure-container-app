"""
Test accessing warrant with ID_NOTATION directly.
"""

import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from app.core.constants import BASE_URL


async def test_warrant_with_id_notation():
    """Test accessing warrant page with ID_NOTATION."""
    print("="*80)
    print("TESTING WARRANT ACCESS WITH ID_NOTATION")
    print("="*80)
    
    wkn = "MJ85T6"
    id_notation = "489859490"
    
    # Test different URL patterns
    urls = [
        f"{BASE_URL}/inf/optionsscheine/detail/uebersicht/uebersicht.html?ID_NOTATION={id_notation}",
        f"{BASE_URL}/inf/optionsscheine/detail/uebersicht/uebersicht.html?SEARCH_VALUE={wkn}",
        f"{BASE_URL}/inf/optionsscheine/detail/uebersicht/uebersicht.html?SEARCH_VALUE={wkn}&ID_NOTATION={id_notation}",
        f"{BASE_URL}/inf/optionsscheine/detail/uebersicht.html?ID_NOTATION={id_notation}",
    ]
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for i, url in enumerate(urls):
            print(f"\n{'='*60}")
            print(f"Test {i+1}: {url}")
            print(f"{'='*60}")
            
            try:
                response = await client.get(url, timeout=30.0)
                print(f"Status: {response.status_code}")
                print(f"Final URL: {response.url}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    
                    # Check if we're on the right page
                    h1 = soup.find('h1')
                    if h1:
                        h1_text = h1.get_text(strip=True)
                        print(f"H1: {h1_text[:100]}")
                        
                        if 'MJ85T6' in h1_text or 'Netflix' in h1_text or 'Morgan Stanley' in h1_text:
                            print(f"✓ Found correct instrument page!")
                            
                            # Look for trading venues
                            print(f"\nSearching for trading venue information...")
                            
                            # Look for tables
                            tables = soup.find_all('table')
                            print(f"Tables found: {len(tables)}")
                            
                            # Look for specific patterns
                            text_content = soup.get_text()
                            if 'LT Morgan Stanley' in text_content:
                                print(f"✓ Found 'LT Morgan Stanley' in page content")
                            
                            # Search for select elements or dropdowns
                            selects = soup.find_all('select')
                            print(f"Select elements: {len(selects)}")
                            for select in selects:
                                select_id = select.get('id', 'no-id')
                                options = select.find_all('option')
                                if len(options) > 1:
                                    print(f"  Select '{select_id}' has {len(options)} options")
                                    for opt in options[:5]:
                                        print(f"    {opt.get('value')}: {opt.get_text(strip=True)[:50]}")
                        else:
                            print(f"✗ Wrong page - expected MJ85T6 instrument")
                    else:
                        print(f"No H1 found")
                        
            except Exception as e:
                print(f"✗ Error: {type(e).__name__}: {e}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_warrant_with_id_notation())
