#!/usr/bin/env python3
"""
Test script for the jail address geocoding system.
"""

import polars as pl
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.append('src')

from jail_events.geocoding.processor import JailAddressProcessor
from jail_events.geocoding.jail_locations import get_jail_locations_df

def test_geocoding_system():
    """Test the geocoding system with sample data."""
    
    print("🧪 Testing Jail Address Geocoding System")
    print("=" * 50)
    
    # Create sample data with various address formats and typos
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
            "Cleaned Facility Name": "Cicero Police Jail",
            "Cleaned Address": "4901 W Cermak Rd, Cicero, IL 60804"
        },
        {
            "Report ID": "R004",
            "Cleaned Facility Name": "Cicero Jail",
            "Cleaned Address": "4901 West Cermak Road, Cicero, Illinois 60804"
        },
        {
            "Report ID": "R005",
            "Cleaned Facility Name": "Lyons Police Department",
            "Cleaned Address": "4200 Lawndale Ave, Lyons, IL 60534"
        },
        {
            "Report ID": "R006",
            "Cleaned Facility Name": "Juvenile Detention Center",
            "Cleaned Address": "1100 S Hamilton Ave, Chicago, IL 60612"
        },
        {
            "Report ID": "R007",
            "Cleaned Facility Name": "Unknown Jail",
            "Cleaned Address": "123 Fake Street, Nowhere, IL 12345"  # This should not match
        },
        {
            "Report ID": "R008",
            "Cleaned Facility Name": "Cook County Jail Division 11",
            "Cleaned Address": "3015 S California Blvd, Chicago, IL 60608"
        }
    ]
    
    # Convert to DataFrame
    df = pl.DataFrame(sample_data)
    
    print(f"📊 Sample data created with {len(df)} records")
    print("\nSample addresses:")
    for i, row in enumerate(df.iter_rows(named=True)):
        print(f"  {i+1}. {row['Cleaned Facility Name']}: {row['Cleaned Address']}")
    
    # Initialize processor
    processor = JailAddressProcessor(similarity_threshold=0.8)
    
    # Process addresses
    print("\n🔍 Processing addresses...")
    df_processed = processor.process_jail_addresses(df)
    
    # Display results
    print("\n📋 Geocoding Results:")
    print("-" * 80)
    
    for row in df_processed.iter_rows(named=True):
        print(f"\nReport ID: {row['Report ID']}")
        print(f"Facility: {row['Cleaned Facility Name']}")
        print(f"Address: {row['Cleaned Address']}")
        
        if row['geocoded_latitude'] is not None:
            print(f"✅ Geocoded: {row['geocoded_latitude']:.4f}, {row['geocoded_longitude']:.4f}")
            print(f"   Confidence: {row['geocoded_confidence']:.2f}")
            print(f"   Method: {row['geocoded_method']}")
            print(f"   Matched Facility: {row['geocoded_facility_name']}")
            print(f"   Facility Type: {row['geocoded_facility_type']}")
        else:
            print("❌ No geocoding match found")
        
        if row['suggested_address']:
            print(f"💡 Suggested: {row['suggested_address']} (confidence: {row['suggestion_confidence']:.2f})")
    
    # Get statistics
    stats = processor.get_processing_stats(df_processed)
    
    print("\n📈 Processing Statistics:")
    print("-" * 30)
    print(f"Total Addresses: {stats.get('total_addresses', 0)}")
    print(f"Successfully Geocoded: {stats.get('successfully_geocoded', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.2%}")
    print(f"High Confidence Matches: {stats.get('high_confidence_matches', 0)}")
    print(f"High Confidence Rate: {stats.get('high_confidence_rate', 0):.2%}")
    print(f"Total Clusters: {stats.get('total_clusters', 0)}")
    print(f"Largest Cluster Size: {stats.get('largest_cluster_size', 0)}")
    
    # Show known jail locations
    print("\n🏛️ Known Cook County Jail Locations:")
    print("-" * 40)
    known_jails = get_jail_locations_df()
    for row in known_jails.iter_rows(named=True):
        print(f"• {row['jail_name']}")
        print(f"  Address: {row['address']}, {row['city']}, {row['state']} {row['zip_code']}")
        print(f"  Coordinates: {row['latitude']:.4f}, {row['longitude']:.4f}")
        print(f"  Type: {row['facility_type']}")
        print()

def test_with_real_data():
    """Test with real data from the jail events dataset."""
    
    print("\n🔍 Testing with Real Jail Events Data")
    print("=" * 50)
    
    # Try to load real data
    data_path = Path("src/jail-events/data/jails-data/output/jails_database_with_links.xlsx")
    
    if not data_path.exists():
        print("❌ Real data file not found. Please run the main pipeline first.")
        return
    
    try:
        # Load the data
        print("📂 Loading real data...")
        df = pl.read_excel(data_path)
        
        # Filter for records with addresses
        df_with_addresses = df.filter(pl.col("Cleaned Address").is_not_null())
        
        print(f"📊 Found {len(df_with_addresses)} records with addresses")
        
        # Take a sample for testing
        sample_size = min(100, len(df_with_addresses))
        df_sample = df_with_addresses.head(sample_size)
        
        print(f"🧪 Testing with {len(df_sample)} sample records")
        
        # Process the sample
        processor = JailAddressProcessor()
        df_processed = processor.process_jail_addresses(df_sample)
        
        # Get statistics
        stats = processor.get_processing_stats(df_processed)
        
        print("\n📈 Real Data Processing Statistics:")
        print("-" * 40)
        print(f"Sample Size: {len(df_sample)}")
        print(f"Successfully Geocoded: {stats.get('successfully_geocoded', 0)}")
        print(f"Success Rate: {stats.get('success_rate', 0):.2%}")
        print(f"High Confidence Matches: {stats.get('high_confidence_matches', 0)}")
        print(f"Total Clusters: {stats.get('total_clusters', 0)}")
        
        # Show some examples
        print("\n📋 Sample Results:")
        print("-" * 20)
        for i, row in enumerate(df_processed.head(5).iter_rows(named=True)):
            print(f"\n{i+1}. {row.get('Cleaned Facility Name', 'Unknown')}")
            print(f"   Address: {row.get('Cleaned Address', 'N/A')}")
            if row.get('geocoded_latitude') is not None:
                print(f"   ✅ Geocoded: {row['geocoded_latitude']:.4f}, {row['geocoded_longitude']:.4f}")
                print(f"   Confidence: {row['geocoded_confidence']:.2f}")
            else:
                print("   ❌ No geocoding match")
        
    except Exception as e:
        print(f"❌ Error loading real data: {e}")

if __name__ == "__main__":
    # Test with sample data
    test_geocoding_system()
    
    # Test with real data if available
    test_with_real_data()
    
    print("\n🎉 Geocoding system test completed!")
