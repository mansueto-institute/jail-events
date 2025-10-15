"""
County-level geocoding for Illinois jails.
Handles placeholder addresses by geocoding to county seats.
"""

import polars as pl
import requests
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

class IllinoisCountyGeocoder:
    """
    Geocodes Illinois county jails to their county seats when specific addresses are not available.
    """
    
    def __init__(self, cache_file: Path = Path("illinois_jail_cache/county_geocoding_cache.json")):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = self._load_cache()
        self.nominatim_geolocator = Nominatim(user_agent="illinois-county-geocoder")
        
        # Illinois county seats mapping
        self.county_seats = {
            "Adams": "Quincy",
            "Alexander": "Cairo", 
            "Bond": "Greenville",
            "Boone": "Belvidere",
            "Brown": "Mount Sterling",
            "Bureau": "Princeton",
            "Calhoun": "Hardin",
            "Carroll": "Mount Carroll",
            "Cass": "Virginia",
            "Champaign": "Urbana",
            "Christian": "Taylorville",
            "Clark": "Marshall",
            "Clay": "Louisville",
            "Clinton": "Carlyle",
            "Coles": "Charleston",
            "Cook": "Chicago",
            "Crawford": "Robinson",
            "Cumberland": "Toledo",
            "DeKalb": "Sycamore",
            "DeWitt": "Clinton",
            "Douglas": "Tuscola",
            "DuPage": "Wheaton",
            "Edgar": "Paris",
            "Edwards": "Albion",
            "Effingham": "Effingham",
            "Fayette": "Vandalia",
            "Ford": "Paxton",
            "Franklin": "Benton",
            "Fulton": "Lewistown",
            "Gallatin": "Shawneetown",
            "Greene": "Carrollton",
            "Grundy": "Morris",
            "Hamilton": "McLeansboro",
            "Hancock": "Carthage",
            "Hardin": "Elizabethtown",
            "Henderson": "Oquawka",
            "Henry": "Cambridge",
            "Iroquois": "Watseka",
            "Jackson": "Murphysboro",
            "Jasper": "Newton",
            "Jefferson": "Mount Vernon",
            "Jersey": "Jerseyville",
            "Jo Daviess": "Galena",
            "Johnson": "Vienna",
            "Kane": "Geneva",
            "Kankakee": "Kankakee",
            "Kendall": "Yorkville",
            "Knox": "Galesburg",
            "Lake": "Waukegan",
            "LaSalle": "Ottawa",
            "Lawrence": "Lawrenceville",
            "Lee": "Dixon",
            "Livingston": "Pontiac",
            "Logan": "Lincoln",
            "Macon": "Decatur",
            "Macoupin": "Carlinville",
            "Madison": "Edwardsville",
            "Marion": "Salem",
            "Marshall": "Lacon",
            "Mason": "Havana",
            "Massac": "Metropolis",
            "McDonough": "Macomb",
            "McHenry": "Woodstock",
            "McLean": "Bloomington",
            "Menard": "Petersburg",
            "Mercer": "Aledo",
            "Monroe": "Waterloo",
            "Montgomery": "Hillsboro",
            "Morgan": "Jacksonville",
            "Moultrie": "Sullivan",
            "Ogle": "Oregon",
            "Peoria": "Peoria",
            "Perry": "Pinckneyville",
            "Piatt": "Monticello",
            "Pike": "Pittsfield",
            "Pope": "Golconda",
            "Pulaski": "Mound City",
            "Putnam": "Hennepin",
            "Randolph": "Chester",
            "Richland": "Olney",
            "Rock Island": "Rock Island",
            "Saline": "Harrisburg",
            "Sangamon": "Springfield",
            "Schuyler": "Rushville",
            "Scott": "Winchester",
            "Shelby": "Shelbyville",
            "St. Clair": "Belleville",
            "Stark": "Toulon",
            "Stephenson": "Freeport",
            "Tazewell": "Pekin",
            "Union": "Jonesboro",
            "Vermilion": "Danville",
            "Wabash": "Mount Carmel",
            "Warren": "Monmouth",
            "Washington": "Nashville",
            "Wayne": "Fairfield",
            "White": "Carmi",
            "Whiteside": "Morrison",
            "Will": "Joliet",
            "Williamson": "Marion",
            "Winnebago": "Rockford",
            "Woodford": "Eureka"
        }
    
    def _load_cache(self) -> Dict[str, Any]:
        """Loads the geocoding cache from a JSON file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Saves the geocoding cache to a JSON file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def geocode_county_seat(self, county_name: str) -> Optional[Dict]:
        """
        Geocodes a county seat for a given county name.
        
        Args:
            county_name: Name of the county (e.g., "Cook County", "Cook", "cook")
            
        Returns:
            Dictionary with geocoding results or None if failed
        """
        # Clean county name
        county_clean = county_name.replace(" County", "").strip().title()
        
        if county_clean not in self.county_seats:
            print(f"⚠️ County seat not found for: {county_name}")
            return None
        
        county_seat = self.county_seats[county_clean]
        cache_key = f"county_seat_{county_clean}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Geocode county seat
            query = f"{county_seat}, {county_clean} County, Illinois, USA"
            location = self.nominatim_geolocator.geocode(query, timeout=10)
            
            if location:
                result = {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "confidence": 0.8,  # Medium confidence for county-level geocoding
                    "method": "county_seat",
                    "formatted_address": location.address,
                    "county_seat": county_seat,
                    "county": county_clean
                }
                self.cache[cache_key] = result
                self._save_cache()
                return result
            else:
                print(f"❌ Could not geocode county seat: {county_seat}")
                return None
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"❌ Error geocoding county seat {county_seat}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error geocoding county seat {county_seat}: {e}")
            return None
    
    def geocode_placeholder_addresses(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Geocodes placeholder addresses by finding the county and geocoding to county seat.
        
        Args:
            df: DataFrame with jail data
            
        Returns:
            DataFrame with additional geocoding data
        """
        print("🏛️ Geocoding placeholder addresses to county seats...")
        
        # Find records with placeholder addresses
        placeholder_mask = df["address"].str.contains("TBD - .* County, IL")
        placeholder_records = df.filter(placeholder_mask)
        
        print(f"📊 Found {len(placeholder_records)} placeholder addresses")
        
        if len(placeholder_records) == 0:
            return df
        
        # Start with the original DataFrame and add missing columns
        result_df = df.clone()
        
        # Add missing columns if they don't exist
        if "county_seat" not in result_df.columns:
            result_df = result_df.with_columns(pl.lit(None, dtype=pl.String).alias("county_seat"))
        if "geocoded_confidence" not in result_df.columns:
            result_df = result_df.with_columns(pl.lit(None, dtype=pl.Float64).alias("geocoded_confidence"))
        if "geocoded_method" not in result_df.columns:
            result_df = result_df.with_columns(pl.lit(None, dtype=pl.String).alias("geocoded_method"))
        if "geocoded_formatted_address" not in result_df.columns:
            result_df = result_df.with_columns(pl.lit(None, dtype=pl.String).alias("geocoded_formatted_address"))
        
        # Process each placeholder record and update in place
        for i, row in enumerate(placeholder_records.iter_rows(named=True)):
            # Extract county name from address
            address = row["address"]
            if "TBD - " in address and " County, IL" in address:
                county_name = address.replace("TBD - ", "").replace(" County, IL", "")
            else:
                county_name = row.get("county", "").replace(" County", "")
            
            # Geocode county seat
            geocoding_result = self.geocode_county_seat(county_name)
            
            if geocoding_result:
                # Update the record with geocoding results
                result_df = result_df.with_columns([
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["latitude"], dtype=pl.Float64))
                    .otherwise(pl.col("latitude"))
                    .alias("latitude"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["longitude"], dtype=pl.Float64))
                    .otherwise(pl.col("longitude"))
                    .alias("longitude"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["confidence"], dtype=pl.Float64))
                    .otherwise(pl.col("geocoded_confidence"))
                    .alias("geocoded_confidence"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["method"], dtype=pl.String))
                    .otherwise(pl.col("geocoded_method"))
                    .alias("geocoded_method"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["formatted_address"], dtype=pl.String))
                    .otherwise(pl.col("geocoded_formatted_address"))
                    .alias("geocoded_formatted_address"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(geocoding_result["county_seat"], dtype=pl.String))
                    .otherwise(pl.col("county_seat"))
                    .alias("county_seat")
                ])
                print(f"✅ Geocoded {county_name} County to {geocoding_result['county_seat']}")
            else:
                # Update with failed status
                result_df = result_df.with_columns([
                    pl.when(pl.col("address") == address)
                    .then(pl.lit(0.0, dtype=pl.Float64))
                    .otherwise(pl.col("geocoded_confidence"))
                    .alias("geocoded_confidence"),
                    pl.when(pl.col("address") == address)
                    .then(pl.lit("failed", dtype=pl.String))
                    .otherwise(pl.col("geocoded_method"))
                    .alias("geocoded_method")
                ])
                print(f"❌ Failed to geocode {county_name} County")
        
        print(f"✅ Geocoded {len(placeholder_records)} placeholder addresses")
        return result_df
    
    def get_geocoding_statistics(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Get statistics about geocoding results."""
        total_records = len(df)
        geocoded_records = len(df.filter(pl.col("latitude").is_not_null()))
        county_seat_geocoded = len(df.filter(pl.col("geocoded_method") == "county_seat"))
        
        return {
            "total_records": total_records,
            "geocoded_records": geocoded_records,
            "geocoding_success_rate": geocoded_records / total_records if total_records > 0 else 0,
            "county_seat_geocoded": county_seat_geocoded,
            "county_seat_rate": county_seat_geocoded / total_records if total_records > 0 else 0
        }

def enhance_illinois_database_with_county_geocoding():
    """Enhance the Illinois database with county-level geocoding."""
    print("🏛️ Enhancing Illinois Database with County-Level Geocoding")
    print("=" * 60)
    
    # Load existing database
    data_dir = Path("data/illinois_jail_analysis")
    db_path = data_dir / "unified_illinois_jails.parquet"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run 'make illinois-db' first.")
        return
    
    # Load data
    df = pl.read_parquet(db_path)
    print(f"📊 Loaded {len(df)} records")
    
    # Initialize county geocoder
    county_geocoder = IllinoisCountyGeocoder()
    
    # Geocode placeholder addresses
    enhanced_df = county_geocoder.geocode_placeholder_addresses(df)
    
    # Get statistics
    stats = county_geocoder.get_geocoding_statistics(enhanced_df)
    
    print(f"\n📈 Geocoding Statistics:")
    print(f"   Total Records: {stats['total_records']}")
    print(f"   Geocoded Records: {stats['geocoded_records']}")
    print(f"   Success Rate: {stats['geocoding_success_rate']:.1%}")
    print(f"   County Seat Geocoded: {stats['county_seat_geocoded']}")
    print(f"   County Seat Rate: {stats['county_seat_rate']:.1%}")
    
    # Save enhanced database
    enhanced_path = data_dir / "unified_illinois_jails_enhanced.parquet"
    enhanced_df.write_parquet(enhanced_path)
    print(f"\n💾 Enhanced database saved to: {enhanced_path}")
    
    # Also update the original database
    enhanced_df.write_parquet(db_path)
    print(f"💾 Original database updated: {db_path}")
    
    return enhanced_df

if __name__ == "__main__":
    enhanced_df = enhance_illinois_database_with_county_geocoding()
    print("\n🎉 County-level geocoding completed!")
    print("💡 Now you should have coordinates for all 110 facilities!")
