"""
Check what the refetched Siemens page actually contains.
"""

import asyncio

import httpx
from bs4 import BeautifulSoup

from app.core.constants import ASSET_CLASS_DETAILS_PATH, BASE_URL
from app.models.basedata import AssetClass


async def examine_refetched_siemens():
    """Examine the refetched page structure."""
    print("="*80)
    print("EXAMINING REFETCHED SIEMENS PAGE")
    print("="*80)
    
    wkn = "723610"
    id_notation = "9385813"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        path = ASSET_CLASS_DETAILS_PATH[AssetClass.STOCK]
        url = f"{BASE_URL}{path}?SEARCH_VALUE={wkn}&ID_NOTATION={id_notation}"
        
        response = await client.get(url, timeout=30.0)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Get all options from marketSelect
        print(f"\n1. ALL OPTIONS FROM #marketSelect:")
        market_select = soup.select_one("#marketSelect")
        if market_select:
            options = market_select.find_all("option")
            id_notations_dict = {}
            for opt in options:
                label = opt.get("label", "")
                value = opt.get("value", "")
                id_notations_dict[label] = value
                print(f"   {label}: {value}")
            
            print(f"\n   Total options: {len(options)}")
            print(f"\n2. LOOKING FOR LIVE TRADING CATEGORIZATION:")
            
            # Now look for td elements with data-label
            lt_venues = soup.find_all("td", {"data-label": "LiveTrading"})
            print(f"   Found {len(lt_venues)} cells with data-label='LiveTrading'")
            
            if lt_venues:
                print(f"   Content:")
                for v in lt_venues:
                    venue_name = v.text.strip()
                    print(f"     '{venue_name}' -> {id_notations_dict.get(venue_name, 'NOT FOUND')}")
            
            print(f"\n3. LOOKING FOR BÖRSE CATEGORIZATION:")
            ex_venues = soup.find_all("td", {"data-label": "Börse"})
            print(f"   Found {len(ex_venues)} cells with data-label='Börse'")
            
            if ex_venues:
                print(f"   Content:")
                for v in ex_venues:
                    venue_name = v.text.strip()
                    print(f"     '{venue_name}' -> {id_notations_dict.get(venue_name, 'NOT FOUND')}")
            
            # Alternative: look for any elements containing LiveTrading or Börse
            print(f"\n4. SEARCHING FOR 'LiveTrading' TEXT:")
            elements_with_lt = soup.find_all(string=lambda text: text and "LiveTrading" in text)
            print(f"   Found {len(elements_with_lt)} elements")
            
            print(f"\n5. SEARCHING FOR 'Börse' TEXT:")
            elements_with_boerse = soup.find_all(string=lambda text: text and "Börse" in text)
            print(f"   Found {len(elements_with_boerse)} elements")
            for elem in elements_with_boerse[:3]:
                print(f"     {elem.strip()[:60]}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(examine_refetched_siemens())
