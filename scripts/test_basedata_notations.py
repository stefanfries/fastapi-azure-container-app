"""
Check what ID_NOTATIONs are in basedata for the warrant.
"""

import asyncio

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.parsers.basedata import parse_base_data
from app.scrapers.scrape_url import fetch_one


async def check_basedata_notations():
    """Check what notations are captured in basedata."""
    print("="*80)
    print("CHECKING BASEDATA ID_NOTATIONS FOR MJ85T6")
    print("="*80)
    
    wkn = "MJ85T6"
    
    basedata = await parse_base_data(wkn)
    
    print(f"\nInstrument: {basedata.name}")
    print(f"WKN: {basedata.wkn}")
    print(f"Asset Class: {basedata.asset_class}")
    print(f"\nDefault ID_NOTATION: {basedata.default_id_notation}")
    print(f"Preferred Exchange Trading: {basedata.preferred_id_notation_exchange_trading}")
    print(f"Preferred Life Trading: {basedata.preferred_id_notation_life_trading}")
    
    print(f"\nID Notations Life Trading:")
    if basedata.id_notations_life_trading:
        for venue, notation in basedata.id_notations_life_trading.items():
            print(f"  {venue}: {notation}")
    else:
        print("  None")
    
    print(f"\nID Notations Exchange Trading:")
    if basedata.id_notations_exchange_trading:
        for venue, notation in basedata.id_notations_exchange_trading.items():
            print(f"  {venue}: {notation}")
    else:
        print("  None")
    
    # Now check what's actually in the HTML
    print(f"\n{'='*80}")
    print("CHECKING HTML FOR ALL ID_NOTATIONS")
    print(f"{'='*80}")
    
    response = await fetch_one(wkn, AssetClass.WARRANT, None)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find the select tag with ID_NOTATION options
    select_tags = soup.find_all("select")
    
    print(f"\nFound {len(select_tags)} select tags")
    
    for idx, select in enumerate(select_tags):
        select_id = select.get('id', 'no-id')
        select_name = select.get('name', 'no-name')
        options = select.find_all('option')
        
        if 'notation' in select_id.lower() or 'notation' in select_name.lower() or len(options) > 1:
            print(f"\nSelect tag #{idx} (id='{select_id}', name='{select_name}'):")
            print(f"  Options ({len(options)}):")
            for option in options:
                value = option.get('value', '')
                text = option.get_text(strip=True)
                selected = 'selected' in option.attrs
                sel_marker = " [SELECTED]" if selected else ""
                print(f"    value={value}: {text}{sel_marker}")
                
                # Check if this matches our expected ID_NOTATIONs
                if value in ["489859490", "489866209"]:
                    print(f"      ✓ This is one of the expected ID_NOTATIONs!")


async def main():
    await check_basedata_notations()
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
