"""
Check the structure of header cells with venue names
"""
import asyncio
import re

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def check_headers():
    wkn = "723610"
    asset_class = AssetClass.STOCK
    id_notation = "9385813"
    
    print(f"Fetching Siemens...\n")
    response = await fetch_one(wkn, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")
    
    tables = soup.find_all("table")
    
    for idx, table in enumerate(tables):
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True) for h in headers]
        
        if "Gestellte" in " ".join(header_texts):
            print(f"=== Life Trading Table (Table {idx}) ===\n")
            
            # Look at ALL headers
            for header_idx, header in enumerate(headers):
                header_text = header.get_text(strip=True)
                print(f"\n--- Header {header_idx}: '{header_text}' ---")
                print(f"HTML: {str(header)[:500]}")
                
                # Check all elements inside
                all_elems = header.find_all(True)
                print(f"Contains {len(all_elems)} sub-elements")
                for elem in all_elems[:5]:
                    print(f"  {elem.name}: {elem.attrs}")
                    if elem.get("onclick"):
                        print(f"    *** onclick: {elem.get('onclick')}")
            
            break

if __name__ == "__main__":
    asyncio.run(check_headers())
