"""
Save and examine the HTML structure for the warrant.
"""

import asyncio

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.scrapers.scrape_url import fetch_one


async def examine_html_structure():
    """Save and examine HTML for the warrant."""
    print("="*80)
    print("EXAMINING HTML STRUCTURE FOR MJ85T6")
    print("="*80)
    
    wkn = "MJ85T6"
    
    response = await fetch_one(wkn, AssetClass.WARRANT, None)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Save HTML to file
    with open("warrant_page.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print(f"\n✓ HTML saved to warrant_page.html")
    
    # Check for #marketSelect
    print(f"\nSearching for #marketSelect...")
    market_select = soup.select("#marketSelect")
    print(f"  Found {len(market_select)} element(s) with id='marketSelect'")
    
    if market_select:
        options = market_select[0].find_all("option")
        print(f"  Options found: {len(options)}")
        for opt in options:
            print(f"    label={opt.get('label')}, value={opt.get('value')}")
    
    # Check for simple-table
    print(f"\nSearching for simple-table...")
    tables = soup.select("body div.grid.grid--no-gutter table.simple-table")
    print(f"  Found {len(tables)} simple-table(s)")
    
    if tables:
        print(f"\n  First table structure:")
        rows = tables[0].select("tr")
        print(f"    Rows: {len(rows)}")
        for i, row in enumerate(rows[:5]):  # First 5 rows
            cells = row.select("td")
            if cells:
                cell_texts = [cell.text.strip()[:50] for cell in cells]
                print(f"      Row {i}: {cell_texts}")
    
    # Check for LiveTrading and Börse labels
    print(f"\nSearching for LiveTrading and Börse data...")
    lt_venues = soup.find_all("td", {"data-label": "LiveTrading"})
    print(f"  LiveTrading cells: {len(lt_venues)}")
    for v in lt_venues[:5]:
        print(f"    {v.text.strip()}")
    
    ex_venues = soup.find_all("td", {"data-label": "Börse"})
    print(f"  Börse cells: {len(ex_venues)}")
    for v in ex_venues[:5]:
        print(f"    {v.text.strip()}")
    
    # Check for any select tags
    print(f"\nSearching for ALL select tags...")
    all_selects = soup.find_all("select")
    print(f"  Found {len(all_selects)} select tag(s)")
    for i, select in enumerate(all_selects):
        print(f"\n  Select {i}:")
        print(f"    id: {select.get('id')}")
        print(f"    name: {select.get('name')}")
        print(f"    class: {select.get('class')}")
        options = select.find_all("option")
        print(f"    options: {len(options)}")
        for opt in options[:3]:
            print(f"      value={opt.get('value')}: {opt.text.strip()[:50]}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(examine_html_structure())
