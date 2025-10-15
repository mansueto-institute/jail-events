"""
Hybrid geocoding approach: Use both Illinois jail database and OSM.
"""

import polars as pl
from typing import Dict, List, Optional, Tuple
from .address_geocoder import IllinoisAddressGeocoder
from .address_cleaner import clean_address, calculate_address_similarity

class HybridJailGeocoder:
    """
    Hybrid geocoder that uses both a pre-built Illinois jail database
    and OSM geocoding for maximum accuracy.
    """
    
    def __init__(self, illinois_jails_db: pl.DataFrame = None):
        self.illinois_jails_db = illinois_jails_db
        self.osm_geocoder = IllinoisAddressGeocoder()
        
    def geocode_with_database_first(self, address: str, facility_name: str = "") -> Optional[Dict]:
        """
        Try to match against Illinois jail database first, then fall back to OSM.
        
        Args:
            address: Address to geocode
            facility_name: Name of the facility
            
        Returns:
            Geocoding result or None
        """
        if not address:
            return None
        
        # Step 1: Try to match against Illinois jail database
        if self.illinois_jails_db is not None:
            db_match = self._match_illinois_database(address, facility_name)
            if db_match:
                return db_match
        
        # Step 2: Fall back to OSM geocoding
        osm_result = self.osm_geocoder.geocode_with_nominatim(address)
        if osm_result:
            # Enhance OSM result with database context
            enhanced_result = self._enhance_osm_result(osm_result, address, facility_name)
            return enhanced_result
        
        return None
    
    def _match_illinois_database(self, address: str, facility_name: str = "") -> Optional[Dict]:
        """Match against the Illinois jail database."""
        if self.illinois_jails_db is None:
            return None
        
        cleaned_address = clean_address(address)
        
        # Try exact address match first
        exact_match = self.illinois_jails_db.filter(
            pl.col("address").map_elements(clean_address, return_dtype=pl.String) == cleaned_address
        )
        
        if len(exact_match) > 0:
            jail = exact_match.row(0, named=True)
            return {
                'latitude': jail['latitude'],
                'longitude': jail['longitude'],
                'formatted_address': jail['address'],
                'confidence': 1.0,
                'source': 'illinois_database',
                'facility_name': jail['name'],
                'facility_type': jail['facility_type'],
                'county': jail['county']
            }
        
        # Try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for row in self.illinois_jails_db.iter_rows(named=True):
            score = calculate_address_similarity(address, row['address'])
            if score > best_score and score >= 0.8:  # High threshold for database matches
                best_score = score
                best_match = row
        
        if best_match:
            return {
                'latitude': best_match['latitude'],
                'longitude': best_match['longitude'],
                'formatted_address': best_match['address'],
                'confidence': best_score,
                'source': 'illinois_database_fuzzy',
                'facility_name': best_match['name'],
                'facility_type': best_match['facility_type'],
                'county': best_match['county']
            }
        
        return None
    
    def _enhance_osm_result(self, osm_result: Dict, address: str, facility_name: str) -> Dict:
        """Enhance OSM result with additional context."""
        enhanced = osm_result.copy()
        
        # Add facility type classification
        enhanced['facility_type'] = self._classify_facility_type(facility_name)
        
        # Add county information
        enhanced['county'] = self._extract_county_from_osm(osm_result)
        
        return enhanced
    
    def _classify_facility_type(self, facility_name: str) -> str:
        """Classify facility type based on name."""
        if not facility_name:
            return "unknown"
        
        name_lower = facility_name.lower()
        
        if any(term in name_lower for term in ['county', 'sheriff']):
            return "county"
        elif any(term in name_lower for term in ['city', 'municipal', 'police']):
            return "municipal"
        elif any(term in name_lower for term in ['juvenile', 'youth']):
            return "juvenile"
        elif any(term in name_lower for term in ['correctional', 'prison']):
            return "correctional"
        else:
            return "unknown"
    
    def _extract_county_from_osm(self, osm_result: Dict) -> str:
        """Extract county from OSM result."""
        address_components = osm_result.get('address_components', {})
        return address_components.get('county', '')

def build_illinois_jail_database_from_osm() -> pl.DataFrame:
    """
    Build Illinois jail database by geocoding known jail addresses.
    This would be a one-time process to create the database.
    """
    
    # Known Illinois jail addresses (this would be much more comprehensive)
    known_jails = [
        {
            "name": "Cook County Jail",
            "address": "2700 S California Ave, Chicago, IL 60608",
            "facility_type": "county",
            "county": "Cook"
        },
        {
            "name": "DuPage County Jail", 
            "address": "501 N County Farm Rd, Wheaton, IL 60187",
            "facility_type": "county",
            "county": "DuPage"
        },
        {
            "name": "Kane County Adult Justice Center",
            "address": "37W755 IL-38, St. Charles, IL 60175", 
            "facility_type": "county",
            "county": "Kane"
        },
        # ... many more would be added here
    ]
    
    geocoder = IllinoisAddressGeocoder()
    geocoded_jails = []
    
    for jail in known_jails:
        print(f"Geocoding {jail['name']}...")
        result = geocoder.geocode_with_nominatim(jail['address'])
        
        if result:
            geocoded_jails.append({
                **jail,
                'latitude': result['latitude'],
                'longitude': result['longitude'],
                'formatted_address': result['formatted_address']
            })
        else:
            print(f"  Failed to geocode {jail['name']}")
    
    return pl.DataFrame(geocoded_jails)

# Example usage
if __name__ == "__main__":
    # Build the database (one-time process)
    print("Building Illinois jail database...")
    illinois_db = build_illinois_jail_database_from_osm()
    
    # Use hybrid geocoder
    hybrid_geocoder = HybridJailGeocoder(illinois_db)
    
    # Test geocoding
    result = hybrid_geocoder.geocode_with_database_first(
        "2700 S California Ave, Chicago, IL 60608",
        "Cook County Jail"
    )
    
    if result:
        print(f"Geocoded: {result['latitude']}, {result['longitude']}")
        print(f"Source: {result['source']}")
        print(f"Confidence: {result['confidence']}")
    else:
        print("Failed to geocode")
