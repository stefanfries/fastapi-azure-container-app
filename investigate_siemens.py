"""
Investigate why trading venues are not extracted for Siemens.
"""

import asyncio

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.scrapers.scrape_url import fetch_one


async def investigate_siemens():
    """Examine Siemens HTML to understand why venues aren't extracted."""
    print("="*80)
    print("INVESTIGATING SIEMENS TRADING VENUES")
    print("="*80)
    
    wkn = "723610"
    
    response = await fetch_one(wkn, AssetClass.STOCK, None)
    soup = BeautifulSoup(response.content, "html.parser")
    
    print(f"\n1. Checking for #marketSelect...")
    market_select = soup.select("#marketSelect")
    print(f"   Found: {len(market_select)} element(s)")
    
    if market_select:
        options = market_select[0].find_all("option")
        print(f"   Options: {len(options)}")
        for opt in options[:10]:
            print(f"     label={opt.get('label')}, value={opt.get('value')}")
    
    print(f"\n2. Checking for simple-table...")
    tables = soup.select("body div.grid.grid--no-gutter table.simple-table")
    print(f"   Found: {len(tables)} table(s)")
    
    if tables:
        print(f"\n   First table rows:")
        rows = tables[0].select("tr")
        for i, row in enumerate(rows[:5]):
            cells = row.select("td")
            if cells:
                print(f"     Row {i}: {[c.text.strip()[:40] for c in cells]}")
    
    print(f"\n3. Checking for LiveTrading cells...")
    lt_cells = soup.find_all("td", {"data-label": "LiveTrading"})
    print(f"   Found: {len(lt_cells)} cell(s)")
    for cell in lt_cells[:5]:
        print(f"     {cell.text.strip()}")
    
    print(f"\n4. Checking for Börse cells...")
    ex_cells = soup.find_all("td", {"data-label": "Börse"})
    print(f"   Found: {len(ex_cells)} cell(s)")
    for cell in ex_cells[:5]:
        print(f"     {cell.text.strip()}")
    
    print(f"\n5. Looking for ALL tables...")
    all_tables = soup.find_all("table")
    print(f"   Total tables: {len(all_tables)}")
    
    for i, table in enumerate(all_tables[:5]):
        print(f"\n   Table {i}:")
        print(f"     class: {table.get('class')}")
        rows = table.find_all("tr")
        if len(rows) > 0:
            first_row_cells = rows[0].find_all(['td', 'th'])
            if first_row_cells:
                headers = [c.text.strip()[:30] for c in first_row_cells]
                print(f"     First row: {headers}")
    
    print(f"\n6. Looking for links with ID_NOTATION...")
    links_with_notation = soup.find_all("a", attrs={"data-plugin": True})
    notation_found = []
    for link in links_with_notation[:10]:
        data_plugin = link.get("data-plugin", "")
        if "ID_NOTATION" in data_plugin:
            print(f"     Found: {data_plugin[:100]}")
            notation_found.append(link)
    
    print(f"\n   Total links with ID_NOTATION in data-plugin: {len(notation_found)}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(investigate_siemens())
