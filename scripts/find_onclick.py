"""
Find the desktop version of cells (visible-lg) with onclick
"""
import asyncio
import re

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def find_onclick_cells():
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
            
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                
                for row_idx, row in enumerate(rows[:2]):
                    print(f"--- Row {row_idx + 1} ---")
                    cells = row.find_all("td")
                    
                    # Get venue name from first cell
                    venue_cell = cells[0]
                    venue_name = venue_cell.get("data-label", "")
                    print(f"Venue: {venue_name}")
                    
                    # Get liquidity value
                    for cell in cells:
                        if cell.get("data-label") == "Gestellte Kurse":
                            gestellte_value = cell.get_text(strip=True)
                            print(f"Gestellte Kurse: {gestellte_value}")
                    
                    # Look for ALL cells with onclick
                    print("\nSearching ALL cells for onclick...")
                    for cell_idx, cell in enumerate(cells):
                        # Check the cell itself
                        if cell.get("onclick"):
                            print(f"  Cell {cell_idx} has onclick: {cell.get('onclick')}")
                        
                        # Check for links with onclick
                        links = cell.find_all("a")
                        for link in links:
                            if link.get("onclick"):
                                print(f"  Cell {cell_idx} link has onclick: {link.get('onclick')}")
                        
                        # Check for buttons
                        buttons = cell.find_all("button")
                        for button in buttons:
                            if button.get("onclick"):
                                print(f"  Cell {cell_idx} button has onclick: {button.get('onclick')}")
                    
                    print()
            
            # Check if there are header-level onclick links
            print("\n=== Checking table headers for venue links ===")
            for header_idx, header in enumerate(headers):
                header_text = header.get_text(strip=True)
                if header_text and "LT " in header_text:
                    print(f"\nHeader {header_idx}: {header_text}")
                    links = header.find_all("a")
                    for link in links:
                        onclick = link.get("onclick", "")
                        if onclick:
                            print(f"  *** FOUND onclick in header: {onclick}")
            
            break

if __name__ == "__main__":
    asyncio.run(find_onclick_cells())
