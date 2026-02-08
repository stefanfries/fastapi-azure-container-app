"""
Test the complete implementation with preferred ID_NOTATION extraction
"""
import asyncio

from app.parsers.basedata import parse_base_data


async def test_complete_implementation():
    print("=" * 80)
    print("Testing Complete Implementation with Preferred ID_NOTATIONs")
    print("=" * 80)
    
    # Test 1: Stock (Siemens)
    print("\n" + "=" * 80)
    print("TEST 1: STOCK - Siemens (WKN: 723610)")
    print("=" * 80)
    
    try:
        basedata = await parse_base_data("723610")
        
        print(f"✓ Name: {basedata.name}")
        print(f"✓ WKN: {basedata.wkn}")
        print(f"✓ Asset Class: {basedata.asset_class}")
        print(f"✓ Default ID_NOTATION: {basedata.default_id_notation}")
        
        print(f"\nLife Trading Venues: {len(basedata.id_notations_life_trading or {})}")
        if basedata.id_notations_life_trading:
            for venue, notation in list(basedata.id_notations_life_trading.items())[:3]:
                print(f"  - {venue}: {notation}")
        
        print(f"\n★★★ PREFERRED Life Trading ID_NOTATION: {basedata.preferred_id_notation_life_trading}")
        
        print(f"\nExchange Trading Venues: {len(basedata.id_notations_exchange_trading or {})}")
        if basedata.id_notations_exchange_trading:
            for venue, notation in list(basedata.id_notations_exchange_trading.items())[:3]:
                print(f"  - {venue}: {notation}")
        
        print(f"\n★★★ PREFERRED Exchange Trading ID_NOTATION: {basedata.preferred_id_notation_exchange_trading}")
        
        # Verify preferred IDs are in the respective dictionaries
        if basedata.preferred_id_notation_life_trading:
            if basedata.preferred_id_notation_life_trading in basedata.id_notations_life_trading.values():
                print("\n✓ Preferred LT ID is in Life Trading venues")
            else:
                print("\n✗ ERROR: Preferred LT ID NOT in Life Trading venues!")
        
        if basedata.preferred_id_notation_exchange_trading:
            if basedata.preferred_id_notation_exchange_trading in basedata.id_notations_exchange_trading.values():
                print("✓ Preferred EX ID is in Exchange Trading venues")
            else:
                print("✗ ERROR: Preferred EX ID NOT in Exchange Trading venues!")
        
    except Exception as e:
        print(f"\n✗ Error parsing Siemens: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Another Stock (Volkswagen)
    print("\n" + "=" * 80)
    print("TEST 2: STOCK - Volkswagen Vz. (WKN: 766403)")
    print("=" * 80)
    
    try:
        basedata = await parse_base_data("766403")
        
        print(f"✓ Name: {basedata.name}")
        print(f"✓ WKN: {basedata.wkn}")
        print(f"✓ Default ID_NOTATION: {basedata.default_id_notation}")
        
        print(f"\n★★★ PREFERRED Life Trading: {basedata.preferred_id_notation_life_trading}")
        print(f"★★★ PREFERRED Exchange Trading: {basedata.preferred_id_notation_exchange_trading}")
        
        print(f"\nTotal LT venues: {len(basedata.id_notations_life_trading or {})}")
        print(f"Total EX venues: {len(basedata.id_notations_exchange_trading or {})}")
        
    except Exception as e:
        print(f"\n✗ Error parsing Volkswagen: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Warrant
    print("\n" + "=" * 80)
    print("TEST 3: WARRANT - Morgan Stanley Netflix (WKN: MJ85T6)")
    print("=" * 80)
    
    try:
        basedata = await parse_base_data("MJ85T6")
        
        print(f"✓ Name: {basedata.name}")
        print(f"✓ WKN: {basedata.wkn}")
        print(f"✓ Default ID_NOTATION: {basedata.default_id_notation}")
        
        print(f"\nLife Trading Venues:")
        if basedata.id_notations_life_trading:
            for venue, notation in basedata.id_notations_life_trading.items():
                print(f"  - {venue}: {notation}")
        
        print(f"\n★★★ PREFERRED Life Trading: {basedata.preferred_id_notation_life_trading}")
        
        print(f"\nExchange Trading Venues:")
        if basedata.id_notations_exchange_trading:
            for venue, notation in basedata.id_notations_exchange_trading.items():
                print(f"  - {venue}: {notation}")
        
        print(f"\n★★★ PREFERRED Exchange Trading: {basedata.preferred_id_notation_exchange_trading}")
        
    except Exception as e:
        print(f"\n✗ Error parsing Warrant: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("All tests completed. Check results above for preferred ID_NOTATIONs.")
    print("Preferred notations should be based on:")
    print("  - Life Trading: Highest 'Gestellte Kurse' value")
    print("  - Exchange Trading: Highest 'Anzahl Kurse' value")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_complete_implementation())
