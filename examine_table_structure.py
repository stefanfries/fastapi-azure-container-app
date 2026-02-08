"""
Extract the complete table structure with liquidity data
"""
import asyncio

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def examine_complete_table():
    # Test with Siemens
    wkn = "723610"
    asset_class = AssetClass.STOCK
    id_notation = "9385813"
    
    print(f"Fetching Siemens with ID_NOTATION {id_notation}...\n")
    response = await fetch_one(wkn, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find the table with "Anzahl Kurse" column
    tables = soup.find_all("table")
    for idx, table in enumerate(tables):
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True) for h in headers]
        
        if "Anzahl Kurse" in header_texts:
            print(f"=== Table {idx}: Exchange Trading Table (Börse) ===")
            print(f"Headers: {header_texts}\n")
            
            # Get all rows
            rows = table.find("tbody").find_all("tr")
            print(f"Found {len(rows)} rows\n")
            
            for i, row in enumerate(rows[:5]):  # First 5 rows
                cells = row.find_all("td")
                
                # Extract venue name
                venue_cell = cells[0] if cells else None
                if venue_cell:
                    # Look for the actual venue name
                    venue_name = venue_cell.get("data-label", "")
                    if not venue_name:
                        # Try to get from text content
                        venue_span = venue_cell.find("span", class_="table__column-mobile-toggle-value")
                        if venue_span:
                            venue_name_elem = venue_span.find("span")
                            if venue_name_elem:
                                venue_name = venue_name_elem.get_text(strip=True)
                    
                    print(f"Row {i+1}: Venue = {venue_name}")
                    
                    # Print all cell values
                    for j, cell in enumerate(cells):
                        value = cell.get_text(strip=True)
                        label = cell.get("data-label", f"Col{j}")
                        print(f"  {label}: {value}")
                    
                    # Look for the selector column with data-selected
                    selector_cell = row.find("td", class_="table__column-selector")
                    if selector_cell:
                        selected = selector_cell.get("data-selected")
                        notation_link = selector_cell.find("a")
                        if notation_link:
                            onclick = notation_link.get("onclick", "")
                            print(f"  *** Selector onclick: {onclick}")
                            print(f"  *** data-selected: {selected}")
                    
                    print()
        
        # Look for Life Trading table
        if "Gestellte Kurse" in " ".join(header_texts) or any("Life" in h or "LiveTrading" in h for h in header_texts):
            print(f"=== Table {idx}: Life Trading Table ===")
            print(f"Headers: {header_texts}\n")
            
            rows = table.find("tbody").find_all("tr")
            print(f"Found {len(rows)} rows\n")
            
            for i, row in enumerate(rows[:5]):
                cells = row.find_all("td")
                venue_cell = cells[0] if cells else None
                if venue_cell:
                    venue_name = venue_cell.get("data-label", "")
                    if not venue_name:
                        venue_span = venue_cell.find("span", class_="table__column-mobile-toggle-value")
                        if venue_span:
                            venue_name_elem = venue_span.find("span")
                            if venue_name_elem:
                                venue_name = venue_name_elem.get_text(strip=True)
                    
                    print(f"Row {i+1}: Venue = {venue_name}")
                    
                    for j, cell in enumerate(cells):
                        value = cell.get_text(strip=True)
                        label = cell.get("data-label", f"Col{j}")
                        print(f"  {label}: {value}")
                    
                    selector_cell = row.find("td", class_="table__column-selector")
                    if selector_cell:
                        selected = selector_cell.get("data-selected")
                        notation_link = selector_cell.find("a")
                        if notation_link:
                            onclick = notation_link.get("onclick", "")
                            print(f"  *** Selector onclick: {onclick}")
                            print(f"  *** data-selected: {selected}")
                    
                    print()

if __name__ == "__main__":
    asyncio.run(examine_complete_table())
