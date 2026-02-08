"""
Debug cell structure more carefully
"""
import asyncio
import re

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def debug_cell_structure():
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
            print(f"=== Life Trading Table (Table {idx}) ===")
            print(f"Headers: {header_texts}\n")
            
            # Find header index for "Gestellte Kurse"
            gestellte_idx = None
            for i, h in enumerate(header_texts):
                if "Gestellte" in h:
                    gestellte_idx = i
                    print(f"'Gestellte Kurse' is at column index {i}\n")
                    break
            
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                print(f"Found {len(rows)} rows\n")
                
                for row_idx, row in enumerate(rows[:2]):  # First 2 rows
                    print(f"--- Row {row_idx + 1} ---")
                    cells = row.find_all("td")
                    print(f"Number of cells: {len(cells)}")
                    
                    for cell_idx, cell in enumerate(cells):
                        print(f"\nCell {cell_idx}:")
                        print(f"  Text: {cell.get_text(strip=True)[:100]}")
                        print(f"  Attributes: {cell.attrs}")
                        print(f"  Classes: {cell.get('class')}")
                        
                        # Check for onclick in links
                        link = cell.find("a")
                        if link:
                            onclick = link.get("onclick", "")
                            if onclick:
                                print(f"  *** FOUND onclick: {onclick}")
                    
                    print("\n")
        
        if "Anzahl Kurse" in header_texts:
            print(f"=== Exchange Trading Table (Table {idx}) ===")
            print(f"Headers: {header_texts}\n")
            
            # Find header index
            anzahl_idx = None
            for i, h in enumerate(header_texts):
                if "Anzahl Kurse" in h:
                    anzahl_idx = i
                    print(f"'Anzahl Kurse' is at column index {i}\n")
                    break
            
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                print(f"Found {len(rows)} rows\n")
                
                for row_idx, row in enumerate(rows[:2]):  # First 2 rows
                    print(f"--- Row {row_idx + 1} ---")
                    cells = row.find_all("td")
                    print(f"Number of cells: {len(cells)}")
                    
                    for cell_idx, cell in enumerate(cells):
                        print(f"\nCell {cell_idx}:")
                        print(f"  Text: {cell.get_text(strip=True)[:100]}")
                        print(f"  Attributes: {cell.attrs}")
                        print(f"  Classes: {cell.get('class')}")
                        
                        link = cell.find("a")
                        if link:
                            onclick = link.get("onclick", "")
                            if onclick:
                                print(f"  *** FOUND onclick: {onclick}")
                    
                    print("\n")

if __name__ == "__main__":
    asyncio.run(debug_cell_structure())
