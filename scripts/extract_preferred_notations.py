"""
Extract complete liquidity data with ID_NOTATIONs
"""
import asyncio
import re

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


def extract_id_notation_from_data_plugin(data_plugin_str):
    """Extract ID_NOTATION from data-plugin attribute"""
    # Pattern: ID_NOTATION=12345
    match = re.search(r'ID_NOTATION=(\d+)', data_plugin_str)
    if match:
        return match.group(1)
    return None

async def extract_all_liquidity():
    wkn = "723610"
    asset_class = AssetClass.STOCK
    id_notation = "9385813"
    
    print(f"Fetching Siemens with ID_NOTATION {id_notation}...\n")
    response = await fetch_one(wkn, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")
    
    tables = soup.find_all("table")
    
    for table in tables:
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True) for h in headers]
        
        # === LIFE TRADING TABLE ===
        if "Gestellte" in " ".join(header_texts):
            print("=" * 80)
            print("LIFE TRADING VENUES")
            print("=" * 80)
            
            # Build mapping: venue_name -> id_notation from headers
            venue_to_id = {}
            for header in headers:
                link = header.find("a")
                if link:
                    data_plugin = link.get("data-plugin", "")
                    if "ID_NOTATION=" in data_plugin:
                        venue_name = header.get_text(strip=True)
                        id_not = extract_id_notation_from_data_plugin(data_plugin)
                        if venue_name and id_not:
                            venue_to_id[venue_name] = id_not
            
            print(f"Found {len(venue_to_id)} Life Trading venues in headers\n")
            
            # Extract liquidity values from tbody
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                
                lt_venues = []
                for row in rows:
                    cells = row.find_all("td")
                    if not cells:
                        continue
                    
                    # Get venue name from first cell's data-label
                    venue_name = cells[0].get("data-label", "")
                    
                    # Get "Gestellte Kurse" value
                    gestellte_value = None
                    for cell in cells:
                        if cell.get("data-label") == "Gestellte Kurse":
                            gestellte_text = cell.get_text(strip=True)
                            # Convert "6.844" to integer 6844
                            gestellte_value = int(gestellte_text.replace(".", "").replace(",", ""))
                            break
                    
                    # Match venue name to ID_NOTATION
                    id_not = venue_to_id.get(venue_name)
                    
                    if venue_name and id_not and gestellte_value is not None:
                        lt_venues.append({
                            "venue": venue_name,
                            "id_notation": id_not,
                            "gestellte_kurse": gestellte_value
                        })
                        print(f"  {venue_name:30} | ID: {id_not:10} | Gestellte Kurse: {gestellte_value:,}")
                
                # Find preferred (highest gestellte_kurse)
                if lt_venues:
                    preferred_lt = max(lt_venues, key=lambda x: x["gestellte_kurse"])
                    print(f"\n  ★★★ PREFERRED Life Trading ★★★")
                    print(f"      Venue: {preferred_lt['venue']}")
                    print(f"      ID_NOTATION: {preferred_lt['id_notation']}")
                    print(f"      Gestellte Kurse: {preferred_lt['gestellte_kurse']:,}")
                    print()
        
        # === EXCHANGE TRADING TABLE ===
        if "Anzahl Kurse" in header_texts:
            print("=" * 80)
            print("EXCHANGE TRADING VENUES")
            print("=" * 80)
            
            # Build mapping: venue_name -> id_notation from headers
            venue_to_id = {}
            for header in headers:
                link = header.find("a")
                if link:
                    data_plugin = link.get("data-plugin", "")
                    if "ID_NOTATION=" in data_plugin:
                        venue_name = header.get_text(strip=True)
                        id_not = extract_id_notation_from_data_plugin(data_plugin)
                        if venue_name and id_not:
                            venue_to_id[venue_name] = id_not
            
            print(f"Found {len(venue_to_id)} Exchange Trading venues in headers\n")
            
            # Extract liquidity values from tbody
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                
                ex_venues = []
                for row in rows:
                    cells = row.find_all("td")
                    if not cells:
                        continue
                    
                    # Get venue name
                    venue_name = cells[0].get("data-label", "")
                    
                    # Get "Anzahl Kurse" value
                    anzahl_value = None
                    for cell in cells:
                        if cell.get("data-label") == "Anzahl Kurse":
                            anzahl_text = cell.get_text(strip=True)
                            # Convert "18.087" to integer 18087
                            anzahl_value = int(anzahl_text.replace(".", "").replace(",", ""))
                            break
                    
                    # Match to ID_NOTATION
                    id_not = venue_to_id.get(venue_name)
                    
                    if venue_name and id_not and anzahl_value is not None:
                        ex_venues.append({
                            "venue": venue_name,
                            "id_notation": id_not,
                            "anzahl_kurse": anzahl_value
                        })
                        print(f"  {venue_name:30} | ID: {id_not:10} | Anzahl Kurse: {anzahl_value:,}")
                
                # Find preferred (highest anzahl_kurse)
                if ex_venues:
                    preferred_ex = max(ex_venues, key=lambda x: x["anzahl_kurse"])
                    print(f"\n  ★★★ PREFERRED Exchange Trading ★★★")
                    print(f"      Venue: {preferred_ex['venue']}")
                    print(f"      ID_NOTATION: {preferred_ex['id_notation']}")
                    print(f"      Anzahl Kurse: {preferred_ex['anzahl_kurse']:,}")
                    print()

if __name__ == "__main__":
    asyncio.run(extract_all_liquidity())
