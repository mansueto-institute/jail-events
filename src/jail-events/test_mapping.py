#!/usr/bin/env python3
"""
Test script for the Illinois jail mapping system.
"""

import polars as pl
from pathlib import Path
import sys
import os

# Add current directory to the path
sys.path.insert(0, '.')

from mapping.folium_map import create_illinois_jail_maps, IllinoisJailFoliumMap

def test_mapping_system():
    """Test the mapping system."""
    
    print("🗺️ Testing Illinois Jail Mapping System")
    print("=" * 50)
    
    # Check if Illinois database exists
    data_dir = Path("data/illinois_jail_analysis")
    if not data_dir.exists():
        print("❌ Illinois database not found. Please run 'make illinois-db' first.")
        return
    
    # Check for unified database
    unified_db_path = data_dir / "unified_illinois_jails.parquet"
    if not unified_db_path.exists():
        print("❌ Unified database not found. Please run 'make illinois-db' first.")
        return
    
    print(f"✅ Found Illinois database: {unified_db_path}")
    
    # Load and inspect data
    df = pl.read_parquet(unified_db_path)
    print(f"📊 Database contains {len(df)} records")
    
    # Check geocoded data
    geocoded = df.filter(pl.col("latitude").is_not_null())
    print(f"📍 Geocoded facilities: {len(geocoded)}")
    
    if len(geocoded) == 0:
        print("❌ No geocoded data found. Cannot create maps.")
        return
    
    # Show facility types
    facility_types = df["facility_type"].value_counts()
    print(f"\n🏛️ Facility Types:")
    for row in facility_types.iter_rows(named=True):
        print(f"   {row['facility_type']}: {row['count']}")
    
    # Show counties
    counties = df["county"].value_counts().sort("count", descending=True)
    print(f"\n🏘️ Top Counties:")
    for row in counties.head(10).iter_rows(named=True):
        if row['county']:  # Skip empty counties
            print(f"   {row['county']}: {row['count']}")
    
    # Test map creation
    print(f"\n🗺️ Creating test maps...")
    
    try:
        # Create map creator
        map_creator = IllinoisJailFoliumMap(str(data_dir))
        
        # Create a test map
        test_map_path = map_creator.create_interactive_map("geocoded", "test_map.html")
        
        if test_map_path:
            print(f"✅ Test map created: {test_map_path}")
            
            # Check file size
            file_size = Path(test_map_path).stat().st_size
            print(f"📁 File size: {file_size:,} bytes")
            
            # Try to open in browser
            map_creator.open_map_in_browser(test_map_path)
        else:
            print("❌ Failed to create test map")
            
    except Exception as e:
        print(f"❌ Error creating maps: {e}")
        return
    
    # Create all map types
    print(f"\n🗺️ Creating all map types...")
    try:
        created_maps = create_illinois_jail_maps()
        
        print(f"\n✅ Created {len(created_maps)} interactive maps:")
        for map_path in created_maps:
            file_size = Path(map_path).stat().st_size
            print(f"   📁 {map_path} ({file_size:,} bytes)")
        
        print(f"\n🎉 Mapping system test completed successfully!")
        print(f"💡 Open any of the HTML files in your browser to view the interactive maps.")
        
    except Exception as e:
        print(f"❌ Error creating all maps: {e}")

def test_map_features():
    """Test specific map features."""
    
    print("\n🧪 Testing Map Features")
    print("=" * 30)
    
    # Test data loading
    data_dir = Path("data/illinois_jail_analysis")
    unified_db_path = data_dir / "unified_illinois_jails.parquet"
    
    if not unified_db_path.exists():
        print("❌ Database not found. Run 'make illinois-db' first.")
        return
    
    # Load data
    df = pl.read_parquet(unified_db_path)
    geocoded = df.filter(pl.col("latitude").is_not_null())
    
    print(f"📊 Testing with {len(geocoded)} geocoded facilities")
    
    # Test different map types
    map_creator = IllinoisJailFoliumMap(str(data_dir))
    
    map_types = ["all", "geocoded", "county", "municipal"]
    
    for map_type in map_types:
        print(f"\n🗺️ Testing {map_type} map...")
        
        try:
            map_path = map_creator.create_interactive_map(map_type, f"test_{map_type}_map.html")
            if map_path:
                file_size = Path(map_path).stat().st_size
                print(f"   ✅ Created: {file_size:,} bytes")
            else:
                print(f"   ❌ Failed to create {map_type} map")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    # Test the mapping system
    test_mapping_system()
    
    # Test specific features
    test_map_features()
    
    print("\n🎉 All mapping tests completed!")
    print("\n💡 Next steps:")
    print("   1. Run 'make map' to create all maps")
    print("   2. Open the HTML files in your browser")
    print("   3. Use the interactive features to explore the data")
    print("   4. Share the maps with your team")
