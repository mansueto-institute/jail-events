#!/usr/bin/env python3
"""
Test script for the Illinois jail address geocoding system.
"""

import polars as pl
from pathlib import Path
import sys
import os

# Add current directory to the path
sys.path.insert(0, '.')

from geocoding.processor import JailAddressProcessor
from geocoding.address_geocoder import IllinoisAddressGeocoder

def test_illinois_geocoding():
    """Test the Illinois geocoding system with sample data."""
    
    print("🧪 Testing Illinois Jail Address Geocoding System")
    print("=" * 60)
    
    # Create sample data with various Illinois jail addresses
    sample_data = [
        {
            "Report ID": "R001",
            "Cleaned Facility Name": "Cook County Jail",
            "Cleaned Address": "2700 S California Ave, Chicago, IL 60608"
        },
        {
            "Report ID": "R002", 
            "Cleaned Facility Name": "Cook County Department of Corrections",
            "Cleaned Address": "2700 South California Avenue, Chicago, Illinois 60608"
        },
        {
            "Report ID": "R003",
            "Cleaned Facility Name": "Cicero Police Department Jail",
            "Cleaned Address": "4901 W Cermak Rd, Cicero, IL 60804"
        },
        {
            "Report ID": "R004",
            "Cleaned Facility Name": "DuPage County Jail",
            "Cleaned Address": "501 N County Farm Rd, Wheaton, IL 60187"
        },
        {
            "Report ID": "R005",
            "Cleaned Facility Name": "Kane County Adult Justice Center",
            "Cleaned Address": "37W755 IL-38, St. Charles, IL 60175"
        },
        {
            "Report ID": "R006",
            "Cleaned Facility Name": "Lake County Jail",
            "Cleaned Address": "25 S Martin Luther King Jr Ave, Waukegan, IL 60085"
        },
        {
            "Report ID": "R007",
            "Cleaned Facility Name": "Will County Adult Detention Facility",
            "Cleaned Address": "95 S Chicago St, Joliet, IL 60432"
        },
        {
            "Report ID": "R008",
            "Cleaned Facility Name": "McHenry County Jail",
            "Cleaned Address": "2200 N Seminary Ave, Woodstock, IL 60098"
        },
        {
            "Report ID": "R009",
            "Cleaned Facility Name": "Winnebago County Jail",
            "Cleaned Address": "650 W State St, Rockford, IL 61102"
        },
        {
            "Report ID": "R010",
            "Cleaned Facility Name": "Peoria County Jail",
            "Cleaned Address": "301 N Maxwell Rd, Peoria, IL 61604"
        },
        {
            "Report ID": "R011",
            "Cleaned Facility Name": "Sangamon County Jail",
            "Cleaned Address": "200 S 9th St, Springfield, IL 62701"
        },
        {
            "Report ID": "R012",
            "Cleaned Facility Name": "Unknown Facility",
            "Cleaned Address": "123 Fake Street, Nowhere, IL 12345"  # This should not match
        }
    ]
    
    # Convert to DataFrame
    df = pl.DataFrame(sample_data)
    
    print(f"📊 Sample data created with {len(df)} records")
    print("\nSample Illinois jail addresses:")
    for i, row in enumerate(df.iter_rows(named=True)):
        print(f"  {i+1}. {row['Cleaned Facility Name']}: {row['Cleaned Address']}")
    
    # Initialize processor
    print("\n🔧 Initializing Illinois geocoding processor...")
    processor = JailAddressProcessor(similarity_threshold=0.8)
    
    # Process addresses
    print("\n🌍 Processing addresses with Illinois geocoding...")
    df_processed = processor.process_jail_addresses(df)
    
    # Display results
    print("\n📋 Illinois Geocoding Results:")
    print("-" * 80)
    
    for row in df_processed.iter_rows(named=True):
        print(f"\nReport ID: {row['Report ID']}")
        print(f"Facility: {row['Cleaned Facility Name']}")
        print(f"Address: {row['Cleaned Address']}")
        print(f"Facility Type: {row.get('facility_type', 'Unknown')}")
        print(f"County: {row.get('geocoded_county', 'Unknown')}")
        
        if row.get('geocoded_latitude') is not None:
            print(f"✅ Geocoded: {row['geocoded_latitude']:.4f}, {row['geocoded_longitude']:.4f}")
            print(f"   Confidence: {row['geocoded_confidence']:.2f}")
            print(f"   Method: {row['geocoded_method']}")
            print(f"   Confidence Category: {row.get('confidence_category', 'Unknown')}")
            if row.get('geocoded_formatted_address'):
                print(f"   Formatted Address: {row['geocoded_formatted_address']}")
        else:
            print("❌ No geocoding match found")
        
        if row.get('suggested_address'):
            print(f"💡 Suggested: {row['suggested_address']} (confidence: {row['suggestion_confidence']:.2f})")
    
    # Get comprehensive statistics
    stats = processor.get_processing_stats(df_processed)
    
    print("\n📈 Illinois Geocoding Statistics:")
    print("-" * 40)
    print(f"Total Addresses: {stats.get('total_addresses', 0)}")
    print(f"Successfully Geocoded: {stats.get('successfully_geocoded', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.2%}")
    print(f"High Confidence Matches: {stats.get('high_confidence_matches', 0)}")
    print(f"High Confidence Rate: {stats.get('high_confidence_rate', 0):.2%}")
    print(f"Average Confidence: {stats.get('average_confidence', 0):.2f}")
    
    print(f"\nTotal Clusters: {stats.get('total_clusters', 0)}")
    print(f"Largest Cluster Size: {stats.get('largest_cluster_size', 0)}")
    
    # Show facility type breakdown
    if 'facility_types' in stats:
        print(f"\nFacility Types:")
        for facility_type, count in stats['facility_types'].items():
            print(f"  - {facility_type}: {count}")
    
    # Show county breakdown
    if 'counties' in stats:
        print(f"\nCounties Found:")
        for county, count in stats['counties'].items():
            if county:  # Skip empty counties
                print(f"  - {county}: {count}")
    
    # Show methods used
    if 'methods_used' in stats:
        print(f"\nGeocoding Methods:")
        for method, count in stats['methods_used'].items():
            print(f"  - {method}: {count}")
    
    return df_processed

def test_geocoding_apis():
    """Test the individual geocoding APIs."""
    
    print("\n🌐 Testing Geocoding APIs")
    print("=" * 40)
    
    geocoder = IllinoisAddressGeocoder()
    
    # Test addresses
    test_addresses = [
        "2700 S California Ave, Chicago, IL 60608",
        "501 N County Farm Rd, Wheaton, IL 60187",
        "37W755 IL-38, St. Charles, IL 60175"
    ]
    
    for address in test_addresses:
        print(f"\nTesting: {address}")
        
        # Test Nominatim
        result = geocoder.geocode_with_nominatim(address)
        if result:
            print(f"  ✅ Nominatim: {result['latitude']:.4f}, {result['longitude']:.4f}")
            print(f"     Confidence: {result['confidence']:.2f}")
            print(f"     Address: {result['formatted_address']}")
        else:
            print(f"  ❌ Nominatim: Failed")

if __name__ == "__main__":
    # Test with sample data
    df_processed = test_illinois_geocoding()
    
    # Test individual APIs
    test_geocoding_apis()
    
    print("\n🎉 Illinois geocoding system test completed!")
    print("\n💡 Next steps:")
    print("   1. Run 'make geocode' to geocode your real data")
    print("   2. Check the geocoding cache for API rate limits")
    print("   3. Consider getting a Here API key for better results")
    print("   4. Review the geocoded data for accuracy")
