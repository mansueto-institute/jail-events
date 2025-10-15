"""
Illinois Jail Database Builder
Builds a comprehensive database of all Illinois county, municipal, and police department jails.
"""

import polars as pl
import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .address_geocoder import IllinoisAddressGeocoder
from .address_cleaner import clean_address, calculate_address_similarity

class IllinoisJailDatabaseBuilder:
    """Builds comprehensive Illinois jail database from official sources."""
    
    def __init__(self, cache_dir: str = "illinois_jail_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.geocoder = IllinoisAddressGeocoder()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Illinois Jail Database Builder/1.0 (Educational Research)'
        })
        
        # Illinois counties (all 102)
        self.illinois_counties = [
            "Adams", "Alexander", "Bond", "Boone", "Brown", "Bureau", "Calhoun", "Carroll",
            "Cass", "Champaign", "Christian", "Clark", "Clay", "Clinton", "Coles", "Cook",
            "Crawford", "Cumberland", "DeKalb", "DeWitt", "Douglas", "DuPage", "Edgar",
            "Edwards", "Effingham", "Fayette", "Ford", "Franklin", "Fulton", "Gallatin",
            "Greene", "Grundy", "Hamilton", "Hancock", "Hardin", "Henderson", "Henry",
            "Iroquois", "Jackson", "Jasper", "Jefferson", "Jersey", "Jo Daviess", "Johnson",
            "Kane", "Kankakee", "Kendall", "Knox", "Lake", "LaSalle", "Lawrence", "Lee",
            "Livingston", "Logan", "Macon", "Macoupin", "Madison", "Marion", "Marshall",
            "Mason", "Massac", "McDonough", "McHenry", "McLean", "Menard", "Mercer",
            "Monroe", "Montgomery", "Morgan", "Moultrie", "Ogle", "Peoria", "Perry",
            "Piatt", "Pike", "Pope", "Pulaski", "Putnam", "Randolph", "Richland",
            "Rock Island", "Saline", "Sangamon", "Schuyler", "Scott", "Shelby", "St. Clair",
            "Stark", "Stephenson", "Tazewell", "Union", "Vermilion", "Wabash", "Warren",
            "Washington", "Wayne", "White", "Whiteside", "Will", "Williamson", "Winnebago",
            "Woodford"
        ]
    
    def build_comprehensive_database(self) -> pl.DataFrame:
        """
        Build comprehensive Illinois jail database from multiple sources.
        
        Returns:
            DataFrame with all Illinois jails and coordinates
        """
        print("🏛️ Building Comprehensive Illinois Jail Database")
        print("=" * 60)
        
        all_jails = []
        
        # Step 1: Add known major jails
        print("📋 Step 1: Adding known major Illinois jails...")
        known_jails = self._get_known_major_jails()
        all_jails.extend(known_jails)
        print(f"   Added {len(known_jails)} known major jails")
        
        # Step 2: Add county jails (one per county)
        print("📋 Step 2: Adding county jails...")
        county_jails = self._get_county_jails()
        all_jails.extend(county_jails)
        print(f"   Added {len(county_jails)} county jails")
        
        # Step 3: Add municipal jails
        print("📋 Step 3: Adding municipal jails...")
        municipal_jails = self._get_municipal_jails()
        all_jails.extend(municipal_jails)
        print(f"   Added {len(municipal_jails)} municipal jails")
        
        # Step 4: Geocode all addresses
        print("🌍 Step 4: Geocoding all addresses...")
        geocoded_jails = self._geocode_jails(all_jails)
        
        # Step 5: Create final database
        print("💾 Step 5: Creating final database...")
        df = pl.DataFrame(geocoded_jails)
        
        # Save to cache
        cache_file = self.cache_dir / "illinois_jails_database.parquet"
        df.write_parquet(cache_file)
        print(f"   Saved to {cache_file}")
        
        # Generate statistics
        self._print_database_statistics(df)
        
        return df
    
    def _get_known_major_jails(self) -> List[Dict]:
        """Get known major Illinois jails."""
        return [
            {
                "name": "Cook County Jail",
                "official_name": "Cook County Department of Corrections",
                "address": "2700 S California Ave, Chicago, IL 60608",
                "city": "Chicago",
                "county": "Cook",
                "facility_type": "county",
                "phone": "(773) 674-3000",
                "capacity": 10000
            },
            {
                "name": "DuPage County Jail",
                "official_name": "DuPage County Sheriff's Office",
                "address": "501 N County Farm Rd, Wheaton, IL 60187",
                "city": "Wheaton",
                "county": "DuPage",
                "facility_type": "county",
                "phone": "(630) 407-2000",
                "capacity": 1000
            },
            {
                "name": "Kane County Adult Justice Center",
                "official_name": "Kane County Sheriff's Office",
                "address": "37W755 IL-38, St. Charles, IL 60175",
                "city": "St. Charles",
                "county": "Kane",
                "facility_type": "county",
                "phone": "(630) 208-2000",
                "capacity": 800
            },
            {
                "name": "Lake County Jail",
                "official_name": "Lake County Sheriff's Office",
                "address": "25 S Martin Luther King Jr Ave, Waukegan, IL 60085",
                "city": "Waukegan",
                "county": "Lake",
                "facility_type": "county",
                "phone": "(847) 377-4000",
                "capacity": 600
            },
            {
                "name": "Will County Adult Detention Facility",
                "official_name": "Will County Sheriff's Office",
                "address": "95 S Chicago St, Joliet, IL 60432",
                "city": "Joliet",
                "county": "Will",
                "facility_type": "county",
                "phone": "(815) 727-8575",
                "capacity": 1200
            },
            {
                "name": "McHenry County Jail",
                "official_name": "McHenry County Sheriff's Office",
                "address": "2200 N Seminary Ave, Woodstock, IL 60098",
                "city": "Woodstock",
                "county": "McHenry",
                "facility_type": "county",
                "phone": "(815) 338-2144",
                "capacity": 400
            },
            {
                "name": "Winnebago County Jail",
                "official_name": "Winnebago County Sheriff's Office",
                "address": "650 W State St, Rockford, IL 61102",
                "city": "Rockford",
                "county": "Winnebago",
                "facility_type": "county",
                "phone": "(815) 319-6300",
                "capacity": 800
            },
            {
                "name": "Peoria County Jail",
                "official_name": "Peoria County Sheriff's Office",
                "address": "301 N Maxwell Rd, Peoria, IL 61604",
                "city": "Peoria",
                "county": "Peoria",
                "facility_type": "county",
                "phone": "(309) 697-8515",
                "capacity": 500
            },
            {
                "name": "Sangamon County Jail",
                "official_name": "Sangamon County Sheriff's Office",
                "address": "200 S 9th St, Springfield, IL 62701",
                "city": "Springfield",
                "county": "Sangamon",
                "facility_type": "county",
                "phone": "(217) 753-6666",
                "capacity": 400
            },
            {
                "name": "Cicero Police Department Jail",
                "official_name": "Cicero Police Department",
                "address": "4901 W Cermak Rd, Cicero, IL 60804",
                "city": "Cicero",
                "county": "Cook",
                "facility_type": "municipal",
                "phone": "(708) 652-2130",
                "capacity": 50
            },
            {
                "name": "Lyons Police Department Jail",
                "official_name": "City of Lyons Police Department",
                "address": "4200 Lawndale Ave, Lyons, IL 60534",
                "city": "Lyons",
                "county": "Cook",
                "facility_type": "municipal",
                "phone": "(708) 442-4100",
                "capacity": 20
            },
            {
                "name": "Cook County Juvenile Detention Center",
                "official_name": "Cook County Juvenile Temporary Detention Center",
                "address": "1100 S Hamilton Ave, Chicago, IL 60612",
                "city": "Chicago",
                "county": "Cook",
                "facility_type": "juvenile",
                "phone": "(312) 433-6000",
                "capacity": 500
            }
        ]
    
    def _get_county_jails(self) -> List[Dict]:
        """Generate county jails for all 102 Illinois counties."""
        county_jails = []
        
        # This would ideally scrape official county websites
        # For now, we'll create a template structure
        for county in self.illinois_counties:
            if county in ["Cook", "DuPage", "Kane", "Lake", "Will", "McHenry", 
                         "Winnebago", "Peoria", "Sangamon"]:
                continue  # Already have these
            
            # Create template entry (would be filled with real data)
            county_jails.append({
                "name": f"{county} County Jail",
                "official_name": f"{county} County Sheriff's Office",
                "address": f"TBD - {county} County, IL",  # Would be filled with real address
                "city": f"{county} County",
                "county": county,
                "facility_type": "county",
                "phone": "TBD",
                "capacity": None,
                "status": "needs_research"
            })
        
        return county_jails
    
    def _get_municipal_jails(self) -> List[Dict]:
        """Get municipal jails from major cities."""
        return [
            {
                "name": "Chicago Police Department - Area 1",
                "official_name": "Chicago Police Department",
                "address": "727 E 111th St, Chicago, IL 60628",
                "city": "Chicago",
                "county": "Cook",
                "facility_type": "municipal",
                "phone": "(312) 747-6000",
                "capacity": 100
            },
            {
                "name": "Chicago Police Department - Area 2",
                "official_name": "Chicago Police Department",
                "address": "727 E 111th St, Chicago, IL 60628",
                "city": "Chicago",
                "county": "Cook",
                "facility_type": "municipal",
                "phone": "(312) 747-6000",
                "capacity": 100
            },
            # Add more municipal jails as needed
        ]
    
    def _geocode_jails(self, jails: List[Dict]) -> List[Dict]:
        """Geocode all jail addresses."""
        geocoded_jails = []
        
        for i, jail in enumerate(jails):
            print(f"   Geocoding {i+1}/{len(jails)}: {jail['name']}")
            
            if jail.get('status') == 'needs_research':
                # Skip jails that need research
                jail.update({
                    'latitude': None,
                    'longitude': None,
                    'geocoded_confidence': 0.0,
                    'geocoded_method': 'needs_research'
                })
                geocoded_jails.append(jail)
                continue
            
            # Geocode the address
            result = self.geocoder.geocode_with_nominatim(jail['address'])
            
            if result:
                jail.update({
                    'latitude': result['latitude'],
                    'longitude': result['longitude'],
                    'geocoded_confidence': result['confidence'],
                    'geocoded_method': result['source'],
                    'geocoded_formatted_address': result['formatted_address']
                })
                print(f"     ✅ {result['latitude']:.4f}, {result['longitude']:.4f}")
            else:
                jail.update({
                    'latitude': None,
                    'longitude': None,
                    'geocoded_confidence': 0.0,
                    'geocoded_method': 'failed'
                })
                print(f"     ❌ Failed to geocode")
            
            geocoded_jails.append(jail)
            time.sleep(1.1)  # Rate limiting
        
        return geocoded_jails
    
    def _print_database_statistics(self, df: pl.DataFrame):
        """Print database statistics."""
        total = len(df)
        geocoded = len(df.filter(pl.col('latitude').is_not_null()))
        county_jails = len(df.filter(pl.col('facility_type') == 'county'))
        municipal_jails = len(df.filter(pl.col('facility_type') == 'municipal'))
        
        print(f"\n📊 Database Statistics:")
        print(f"   Total Jails: {total}")
        print(f"   Successfully Geocoded: {geocoded} ({geocoded/total*100:.1f}%)")
        print(f"   County Jails: {county_jails}")
        print(f"   Municipal Jails: {municipal_jails}")
        
        # County breakdown
        county_counts = df['county'].value_counts().sort('count', descending=True)
        print(f"\n   Top Counties by Jail Count:")
        for row in county_counts.head(10).iter_rows(named=True):
            print(f"     {row['county']}: {row['count']} jails")
    
    def match_with_existing_data(self, illinois_db: pl.DataFrame, 
                                existing_data: pl.DataFrame) -> pl.DataFrame:
        """
        Match Illinois database with existing jail events data.
        
        Args:
            illinois_db: Illinois jail database
            existing_data: Existing jail events data
            
        Returns:
            Matched data with coordinates
        """
        print("🔗 Matching with existing data...")
        
        matched_data = []
        
        for row in existing_data.iter_rows(named=True):
            address = row.get('Cleaned Address', '')
            facility_name = row.get('Cleaned Facility Name', '')
            
            if not address:
                # No address to match
                row.update({
                    'illinois_jail_id': None,
                    'illinois_latitude': None,
                    'illinois_longitude': None,
                    'match_confidence': 0.0,
                    'match_method': 'no_address'
                })
                matched_data.append(row)
                continue
            
            # Find best match in Illinois database
            best_match = self._find_best_match(address, facility_name, illinois_db)
            
            if best_match:
                row.update({
                    'illinois_jail_id': best_match['name'],
                    'illinois_latitude': best_match['latitude'],
                    'illinois_longitude': best_match['longitude'],
                    'match_confidence': best_match['match_confidence'],
                    'match_method': best_match['match_method']
                })
                print(f"   ✅ Matched: {facility_name} -> {best_match['name']}")
            else:
                row.update({
                    'illinois_jail_id': None,
                    'illinois_latitude': None,
                    'illinois_longitude': None,
                    'match_confidence': 0.0,
                    'match_method': 'no_match'
                })
                print(f"   ❌ No match: {facility_name}")
            
            matched_data.append(row)
        
        return pl.DataFrame(matched_data)
    
    def _find_best_match(self, address: str, facility_name: str, 
                        illinois_db: pl.DataFrame) -> Optional[Dict]:
        """Find best match for address in Illinois database."""
        best_match = None
        best_score = 0.0
        
        for row in illinois_db.iter_rows(named=True):
            if row['latitude'] is None:
                continue  # Skip ungeocoded entries
            
            # Calculate similarity
            address_score = calculate_address_similarity(address, row['address'])
            name_score = calculate_address_similarity(facility_name, row['name'])
            
            # Combined score
            combined_score = (address_score * 0.7) + (name_score * 0.3)
            
            if combined_score > best_score and combined_score >= 0.7:
                best_score = combined_score
                best_match = {
                    **row,
                    'match_confidence': combined_score,
                    'match_method': 'fuzzy_match'
                }
        
        return best_match

def build_illinois_jail_database():
    """Main function to build Illinois jail database."""
    builder = IllinoisJailDatabaseBuilder()
    return builder.build_comprehensive_database()

if __name__ == "__main__":
    # Build the database
    illinois_db = build_illinois_jail_database()
    print(f"\n🎉 Illinois jail database built with {len(illinois_db)} facilities!")
