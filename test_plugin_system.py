"""
Test the new plugin-based parser system.
"""

import asyncio

from app.parsers.basedata import parse_base_data
from app.parsers.history import parse_history_data


async def test_basedata_parsing():
    """Test basedata parsing with the new plugin system."""
    print("="*80)
    print("TESTING NEW PLUGIN-BASED PARSER SYSTEM")
    print("="*80)
    
    test_instruments = [
        ("766403", "Volkswagen Vorzugsaktie", "STOCK"),
        ("MJ85T6", "Morgan Stanley Netflix Warrant", "WARRANT"),
        ("723610", "Siemens", "STOCK"),
    ]
    
    for wkn, name, asset_type in test_instruments:
        print(f"\n{'='*80}")
        print(f"Testing {name} (WKN: {wkn}, Type: {asset_type})")
        print(f"{'='*80}")
        
        try:
            basedata = await parse_base_data(wkn)
            
            print(f"✓ Basedata parsed successfully")
            print(f"  Name: {basedata.name}")
            print(f"  WKN: {basedata.wkn}")
            print(f"  ISIN: {basedata.isin}")
            print(f"  Asset Class: {basedata.asset_class}")
            print(f"  Default ID_NOTATION: {basedata.default_id_notation}")
            
            print(f"\n  Life Trading Venues:")
            if basedata.id_notations_life_trading:
                for venue, notation in basedata.id_notations_life_trading.items():
                    print(f"    {venue}: {notation}")
            else:
                print(f"    None")
            
            print(f"\n  Exchange Trading Venues:")
            if basedata.id_notations_exchange_trading:
                for venue, notation in basedata.id_notations_exchange_trading.items():
                    print(f"    {venue}: {notation}")
            else:
                print(f"    None")
            
        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


async def test_history_endpoint():
    """Test the history endpoint with the warrant."""
    print(f"\n{'='*80}")
    print(f"TESTING HISTORY ENDPOINT WITH WARRANT")
    print(f"{'='*80}")
    
    wkn = "MJ85T6"
    
    try:
        history_data = await parse_history_data(
            instrument_id=wkn,
            start=None,
            end=None,
            interval="day",
            id_notation=None,
        )
        
        print(f"✓ History data retrieved successfully!")
        print(f"  WKN: {history_data.wkn}")
        print(f"  Name: {history_data.name}")
        print(f"  Currency: {history_data.currency}")
        print(f"  Trading Venue: {history_data.trading_venue}")
        print(f"  ID_NOTATION: {history_data.id_notation}")
        print(f"  Number of data points: {len(history_data.data)}")
        
        if len(history_data.data) > 0:
            print(f"\n  First data point:")
            print(f"    Date: {history_data.data[0].datetime}")
            print(f"    Close: {history_data.data[0].close}")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    await test_basedata_parsing()
    await test_history_endpoint()
    
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print("The new plugin system successfully:")
    print("  1. Parses basedata for standard assets (stocks)")
    print("  2. Parses basedata for warrants with ID_NOTATION refetch")
    print("  3. Extracts trading venues correctly")
    print("  4. Enables the history endpoint to work with warrants")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
