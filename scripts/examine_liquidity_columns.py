"""
Examine the HTML structure to find liquidity columns:
- "Gestellte Kurse" for Life Trading venues
- "Anzahl Kurse" for Exchange Trading venues
"""
import asyncio

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def examine_liquidity_data():
    # Test with Siemens (has many venues)
    wkn = "723610"
    asset_class = AssetClass.STOCK
    id_notation = "9385813"  # Known default_id_notation
    
    print(f"Fetching Siemens with ID_NOTATION {id_notation}...")
    response = await fetch_one(wkn, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Look for the marketSelect dropdown
    market_select = soup.find("select", {"id": "marketSelect"})
    if market_select:
        print(f"\n✓ Found #marketSelect with {len(market_select.find_all('option'))} options")
    
    # Look for table with liquidity data
    print("\n=== Searching for liquidity tables ===")
    
    # Find all tables
    tables = soup.find_all("table")
    print(f"Found {len(tables)} tables in page")
    
    for idx, table in enumerate(tables):
        # Check if table has "Gestellte Kurse" or "Anzahl Kurse"
        table_text = table.get_text()
        if "Gestellte Kurse" in table_text or "Anzahl Kurse" in table_text:
            print(f"\n--- Table {idx} contains liquidity data ---")
            print(table.prettify()[:1000])
            
    # Look for specific cells with these labels
    print("\n=== Searching for cells with 'Gestellte Kurse' ===")
    cells = soup.find_all(string=lambda text: text and "Gestellte Kurse" in text)
    print(f"Found {len(cells)} cells mentioning 'Gestellte Kurse'")
    for cell in cells[:3]:
        parent = cell.parent
        print(f"\nCell: {cell.strip()}")
        print(f"Parent tag: {parent.name}")
        print(f"Parent: {parent}")
        
    print("\n=== Searching for cells with 'Anzahl Kurse' ===")
    cells = soup.find_all(string=lambda text: text and "Anzahl Kurse" in text)
    print(f"Found {len(cells)} cells mentioning 'Anzahl Kurse'")
    for cell in cells[:3]:
        parent = cell.parent
        print(f"\nCell: {cell.strip()}")
        print(f"Parent tag: {parent.name}")
        print(f"Parent: {parent}")
    
    # Look at the structure around marketSelect
    print("\n=== Structure around #marketSelect ===")
    if market_select:
        # Get parent containers
        parent = market_select.parent
        print(f"Parent: {parent.name} with classes {parent.get('class')}")
        
        # Look for siblings or nearby elements
        container = market_select.find_parent(["div", "section", "article"])
        if container:
            print(f"\nContainer: {container.name} with classes {container.get('class')}")
            # Look for any data-* attributes
            all_elements = container.find_all(True)
            for elem in all_elements[:20]:
                if elem.get("data-value") or elem.get("data-label") or elem.name == "td":
                    print(f"  {elem.name}: {elem.get_text(strip=True)[:50]} | attrs: {elem.attrs}")

if __name__ == "__main__":
    asyncio.run(examine_liquidity_data())
