"""
Analyze the warrant HTML to understand its structure for trading venues.
"""

import asyncio
import re

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.scrapers.scrape_url import fetch_one


async def analyze_warrant_structure():
    """Analyze warrant HTML structure in detail."""
    print("="*80)
    print("DETAILED WARRANT HTML ANALYSIS")
    print("="*80)
    
    wkn = "MJ85T6"
    response = await fetch_one(wkn, AssetClass.WARRANT, None)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Look for the URL parameter to see if ID_NOTATION is there
    print(f"\nCurrent page URL:")
    print(f"  {response.url}")
    
    # Check for ID_NOTATION in links
    print(f"\nSearching for links with ID_NOTATION parameter...")
    all_links = soup.find_all('a', href=True)
    notation_links = [link for link in all_links if 'ID_NOTATION' in link['href']]
    
    print(f"  Found {len(notation_links)} links with ID_NOTATION")
    
    notation_ids = set()
    for link in notation_links[:10]:
        href = link['href']
        # Extract ID_NOTATION value
        match = re.search(r'ID_NOTATION[=:](\d+)', href)
        if match:
            notation_id = match.group(1)
            notation_ids.add(notation_id)
            link_text = link.get_text(strip=True)[:80]
            print(f"    ID_NOTATION={notation_id}: {link_text}")
    
    print(f"\n  Unique ID_NOTATIONs found: {notation_ids}")
    
    # Look for data-plugin attributes (mentioned in original code)
    print(f"\nSearching for elements with data-plugin attribute...")
    data_plugin_elements = soup.find_all(attrs={"data-plugin": True})
    print(f"  Found {len(data_plugin_elements)} elements with data-plugin")
    
    for elem in data_plugin_elements[:5]:
        plugin_data = elem.get('data-plugin')
        if 'ID_NOTATION' in plugin_data:
            print(f"    {plugin_data[:150]}")
    
    # Look for any tables
    print(f"\nSearching for ALL tables...")
    all_tables = soup.find_all('table')
    print(f"  Found {len(all_tables)} table(s)")
    
    for i, table in enumerate(all_tables[:3]):
        print(f"\n  Table {i}:")
        print(f"    class: {table.get('class')}")
        print(f"    id: {table.get('id')}")
        rows = table.find_all('tr')
        print(f"    rows: {len(rows)}")
        
        # Check first few rows
        for j, row in enumerate(rows[:3]):
            cells = row.find_all(['td', 'th'])
            if cells:
                cell_texts = [cell.get_text(strip=True)[:40] for cell in cells]
                print(f"      Row {j}: {cell_texts}")
    
    # Look for any divs or sections that might contain trading venue info
    print(f"\nSearching for sections with 'Börse', 'Trading', or 'Handelsplatz'...")
    search_terms = ['Börse', 'Trading', 'Handelsplatz', 'Markt']
    
    for term in search_terms:
        elements = soup.find_all(string=re.compile(term, re.IGNORECASE))
        if elements:
            print(f"\n  Found '{term}' in {len(elements)} element(s):")
            for elem in elements[:3]:
                parent = elem.parent
                print(f"    Parent tag: {parent.name}, class: {parent.get('class')}")
                print(f"    Text: {elem.strip()[:100]}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(analyze_warrant_structure())
