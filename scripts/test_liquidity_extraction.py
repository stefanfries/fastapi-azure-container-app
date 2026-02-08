"""
Extract venue names with their ID_NOTATIONs and liquidity values
"""
import asyncio
import re

from bs4 import BeautifulSoup

from app.core.constants import AssetClass
from app.scrapers.scrape_url import fetch_one


async def extract_venues_with_liquidity():
    # Test with Siemens
    wkn = "723610"
    asset_class = AssetClass.STOCK
    id_notation = "9385813"
    
    print(f"Fetching Siemens with ID_NOTATION {id_notation}...\n")
    response = await fetch_one(wkn, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find the Life Trading table (has "Gestellte Kurse" column)
    tables = soup.find_all("table")
    
    for table in tables:
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True) for h in headers]
        
        # Life Trading table
        if "Gestellte" in " ".join(header_texts) or "LiveTrading" in header_texts:
            print("=" * 70)
            print("LIFE TRADING VENUES (LiveTrading)")
            print("=" * 70)
            
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
            
            lt_venues = []
            for row in rows:
                cells = row.find_all("td")
                if not cells:
                    continue
                
                # Get venue name from data-label
                venue_name = cells[0].get("data-label", "")
                
                # Get "Gestellte Kurse" value (column index depends on headers)
                gestellte_kurse_value = None
                for cell in cells:
                    if cell.get("data-label") == "Gestellte Kurse":
                        gestellte_kurse_value = cell.get_text(strip=True)
                        # Convert "6.799" to integer 6799
                        gestellte_kurse_value = int(gestellte_kurse_value.replace(".", "").replace(",", ""))
                        break
                
                # Get ID_NOTATION from onclick attribute in selector column
                id_notation_value = None
                selector_cell = row.find("td", class_="table__column-selector")
                if selector_cell:
                    link = selector_cell.find("a")
                    if link:
                        onclick = link.get("onclick", "")
                        # Extract ID_NOTATION from onclick like: changeQuotation('3240541')
                        match = re.search(r"changeQuotation\('(\d+)'\)", onclick)
                        if match:
                            id_notation_value = match.group(1)
                
                if venue_name and id_notation_value and gestellte_kurse_value is not None:
                    lt_venues.append({
                        "venue": venue_name,
                        "id_notation": id_notation_value,
                        "gestellte_kurse": gestellte_kurse_value
                    })
                    print(f"  {venue_name:30} | ID: {id_notation_value:10} | Gestellte Kurse: {gestellte_kurse_value:,}")
            
            # Find preferred (highest gestellte_kurse)
            if lt_venues:
                preferred_lt = max(lt_venues, key=lambda x: x["gestellte_kurse"])
                print(f"\n  *** PREFERRED Life Trading: {preferred_lt['venue']}")
                print(f"      ID_NOTATION: {preferred_lt['id_notation']}")
                print(f"      Gestellte Kurse: {preferred_lt['gestellte_kurse']:,}\n")
        
        # Exchange Trading table
        if "Anzahl Kurse" in header_texts:
            print("=" * 70)
            print("EXCHANGE TRADING VENUES (Börse)")
            print("=" * 70)
            
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
            
            ex_venues = []
            for row in rows:
                cells = row.find_all("td")
                if not cells:
                    continue
                
                # Get venue name from data-label
                venue_name = cells[0].get("data-label", "")
                
                # Get "Anzahl Kurse" value
                anzahl_kurse_value = None
                for cell in cells:
                    if cell.get("data-label") == "Anzahl Kurse":
                        anzahl_kurse_value = cell.get_text(strip=True)
                        # Convert "18.033" to integer 18033
                        anzahl_kurse_value = int(anzahl_kurse_value.replace(".", "").replace(",", ""))
                        break
                
                # Get ID_NOTATION from onclick
                id_notation_value = None
                selector_cell = row.find("td", class_="table__column-selector")
                if selector_cell:
                    link = selector_cell.find("a")
                    if link:
                        onclick = link.get("onclick", "")
                        match = re.search(r"changeQuotation\('(\d+)'\)", onclick)
                        if match:
                            id_notation_value = match.group(1)
                
                if venue_name and id_notation_value and anzahl_kurse_value is not None:
                    ex_venues.append({
                        "venue": venue_name,
                        "id_notation": id_notation_value,
                        "anzahl_kurse": anzahl_kurse_value
                    })
                    print(f"  {venue_name:30} | ID: {id_notation_value:10} | Anzahl Kurse: {anzahl_kurse_value:,}")
            
            # Find preferred (highest anzahl_kurse)
            if ex_venues:
                preferred_ex = max(ex_venues, key=lambda x: x["anzahl_kurse"])
                print(f"\n  *** PREFERRED Exchange Trading: {preferred_ex['venue']}")
                print(f"      ID_NOTATION: {preferred_ex['id_notation']}")
                print(f"      Anzahl Kurse: {preferred_ex['anzahl_kurse']:,}\n")

if __name__ == "__main__":
    asyncio.run(extract_venues_with_liquidity())
