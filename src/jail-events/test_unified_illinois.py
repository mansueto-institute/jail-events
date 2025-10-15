#!/usr/bin/env python3
"""
Test script for the unified Illinois jail database system.
"""

import polars as pl
from pathlib import Path
import sys
import os

# Add current directory to the path
sys.path.insert(0, '.')

from geocoding.unified_processor import process_illinois_jail_data
from geocoding.illinois_database_builder import build_illinois_jail_database

def test_illinois_database_builder():
    """Test the Illinois database builder."""
    
    print("🧪 Testing Illinois Database Builder")
    print("=" * 50)
    
    # Build Illinois database
    print("Building Illinois jail database...")
    illinois_db = build_illinois_jail_database()
    
    print(f"\n📊 Illinois Database Results:")
    print(f"   Total Facilities: {len(illinois_db)}")
    
    # Show geocoding results
    geocoded = illinois_db.filter(pl.col('latitude').is_not_null())
    print(f"   Successfully Geocoded: {len(geocoded)} ({len(geocoded)/len(illinois_db)*100:.1f}%)")
    
    # Show facility types
    facility_types = illinois_db['facility_type'].value_counts()
    print(f"\n   Facility Types:")
    for row in facility_types.iter_rows(named=True):
        print(f"     {row['facility_type']}: {row['count']}")
    
    # Show counties
    counties = illinois_db['county'].value_counts().sort('count', descending=True)
    print(f"\n   Top Counties:")
    for row in counties.head(10).iter_rows(named=True):
        print(f"     {row['county']}: {row['count']} facilities")
    
    # Show some examples
    print(f"\n   Sample Facilities:")
    for i, row in enumerate(illinois_db.head(5).iter_rows(named=True)):
        print(f"     {i+1}. {row['name']}")
        print(f"        Address: {row['address']}")
        if row['latitude']:
            print(f"        Coordinates: {row['latitude']:.4f}, {row['longitude']:.4f}")
        else:
            print(f"        Coordinates: Not geocoded")
        print()
    
    return illinois_db

def test_unified_processor():
    """Test the unified processor with sample data."""
    
    print("\n🧪 Testing Unified Processor")
    print("=" * 50)
    
    # Create sample existing data
    sample_data = [
        {
            "Report ID": "R001",
            "Cleaned Facility Name": "Cook County Jail",
            "Cleaned Address": "2700 S California Ave, Chicago, IL 60608"
        },
        {
            "Report ID": "R002",
            "Cleaned Facility Name": "DuPage County Jail",
            "Cleaned Address": "501 N County Farm Rd, Wheaton, IL 60187"
        },
        {
            "Report ID": "R003",
            "Cleaned Facility Name": "Unknown Jail",
            "Cleaned Address": "123 Fake Street, Nowhere, IL 12345"
        }
    ]
    
    # Save sample data
    sample_df = pl.DataFrame(sample_data)
    sample_path = Path("sample_jail_data.xlsx")
    sample_df.write_excel(sample_path)
    
    print(f"Created sample data with {len(sample_df)} records")
    
    try:
        # Process with unified processor
        print("Processing with unified processor...")
        results = process_illinois_jail_data(str(sample_path))
        
        print(f"\n📊 Unified Processing Results:")
        print(f"   Illinois Database: {len(results['illinois_database'])} facilities")
        print(f"   Matched Data: {len(results['matched_data'])} records")
        print(f"   Unified Database: {len(results['unified_database'])} total records")
        
        # Show match results
        matched = results['matched_data'].filter(pl.col('illinois_latitude').is_not_null())
        print(f"   Successfully Matched: {len(matched)} records")
        
        if len(matched) > 0:
            print(f"\n   Match Examples:")
            for i, row in enumerate(matched.iter_rows(named=True)):
                print(f"     {i+1}. {row['Cleaned Facility Name']}")
                print(f"        Matched to: {row['illinois_jail_id']}")
                print(f"        Confidence: {row['match_confidence']:.2f}")
                print(f"        Coordinates: {row['illinois_latitude']:.4f}, {row['illinois_longitude']:.4f}")
                print()
        
        return results
        
    finally:
        # Clean up sample file
        if sample_path.exists():
            sample_path.unlink()

def test_dashboard_export():
    """Test dashboard export functionality."""
    
    print("\n🧪 Testing Dashboard Export")
    print("=" * 50)
    
    # Check if output files exist
    output_dir = Path("data/illinois_jail_analysis")
    
    if not output_dir.exists():
        print("   ❌ Output directory not found. Run unified processor first.")
        return
    
    files_to_check = [
        "illinois_jails_database.parquet",
        "jail_events_with_coordinates.parquet", 
        "unified_illinois_jails.parquet",
        "illinois_jails_for_dashboard.xlsx"
    ]
    
    print("   Checking output files:")
    for file_name in files_to_check:
        file_path = output_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"     ✅ {file_name} ({size:,} bytes)")
        else:
            print(f"     ❌ {file_name} (not found)")
    
    # Check Excel file specifically
    excel_path = output_dir / "illinois_jails_for_dashboard.xlsx"
    if excel_path.exists():
        print(f"\n   📊 Dashboard Excel file ready!")
        print(f"   📁 Location: {excel_path.absolute()}")
        print(f"   💡 This file can be used for mapping and dashboard creation")

if __name__ == "__main__":
    print("🚀 Testing Unified Illinois Jail System")
    print("=" * 60)
    
    # Test 1: Illinois database builder
    illinois_db = test_illinois_database_builder()
    
    # Test 2: Unified processor
    results = test_unified_processor()
    
    # Test 3: Dashboard export
    test_dashboard_export()
    
    print("\n🎉 All tests completed!")
    print("\n💡 Next steps:")
    print("   1. Run 'make illinois-db' to process your real data")
    print("   2. Check the 'data/illinois_jail_analysis' directory")
    print("   3. Use the Excel file for dashboard creation")
    print("   4. Review the unified database for accuracy")
