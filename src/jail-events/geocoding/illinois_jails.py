"""
Illinois Jail Locations Database
Comprehensive database of all Illinois county, municipal, and police department jails.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import polars as pl
import requests
import time
import json
from pathlib import Path

@dataclass
class IllinoisJail:
    """Represents an Illinois jail facility."""
    name: str
    official_name: str
    address: str
    city: str
    county: str
    state: str
    zip_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    facility_type: str = "unknown"  # 'county', 'municipal', 'police', 'juvenile'
    phone: Optional[str] = None
    capacity: Optional[int] = None
    status: str = "active"  # 'active', 'closed', 'temporary'

# Illinois Counties (all 102 counties)
ILLINOIS_COUNTIES = [
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

class IllinoisJailGeocoder:
    """Geocoder for Illinois jail facilities using multiple APIs."""
    
    def __init__(self, use_cache: bool = True, cache_file: str = "illinois_jails_cache.json"):
        self.use_cache = use_cache
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Illinois Jail Geocoder/1.0 (Educational Research)'
        })
    
    def _load_cache(self) -> Dict:
        """Load geocoding cache from file."""
        if self.use_cache and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save geocoding cache to file."""
        if self.use_cache:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
    
    def geocode_with_nominatim(self, address: str, state: str = "Illinois") -> Optional[Dict]:
        """
        Geocode address using OpenStreetMap Nominatim API.
        
        Args:
            address: Address to geocode
            state: State name for context
            
        Returns:
            Dictionary with geocoding results or None
        """
        if not address:
            return None
        
        # Check cache first
        cache_key = f"nominatim_{address}_{state}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Construct search query
            query = f"{address}, {state}, USA"
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'addressdetails': 1,
                'limit': 1,
                'countrycodes': 'us'
            }
            
            # Make request with rate limiting
            time.sleep(1)  # Respect rate limits
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                geocoded = {
                    'latitude': float(result['lat']),
                    'longitude': float(result['lon']),
                    'formatted_address': result.get('display_name', ''),
                    'confidence': self._calculate_confidence(result, address),
                    'source': 'nominatim'
                }
                
                # Cache result
                self.cache[cache_key] = geocoded
                return geocoded
                
        except Exception as e:
            print(f"Error geocoding with Nominatim: {e}")
        
        return None
    
    def geocode_with_here(self, address: str, api_key: str) -> Optional[Dict]:
        """
        Geocode address using Here API.
        
        Args:
            address: Address to geocode
            api_key: Here API key
            
        Returns:
            Dictionary with geocoding results or None
        """
        if not address or not api_key:
            return None
        
        # Check cache first
        cache_key = f"here_{address}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            url = "https://geocode.search.hereapi.com/v1/geocode"
            params = {
                'q': address,
                'apikey': api_key,
                'in': 'countryCode:USA'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('items') and len(data['items']) > 0:
                item = data['items'][0]
                position = item['position']
                geocoded = {
                    'latitude': position['lat'],
                    'longitude': position['lng'],
                    'formatted_address': item.get('title', ''),
                    'confidence': self._calculate_here_confidence(item, address),
                    'source': 'here'
                }
                
                # Cache result
                self.cache[cache_key] = geocoded
                return geocoded
                
        except Exception as e:
            print(f"Error geocoding with Here API: {e}")
        
        return None
    
    def _calculate_confidence(self, result: Dict, original_address: str) -> float:
        """Calculate confidence score for Nominatim results."""
        # Simple confidence calculation based on address components
        address_parts = original_address.lower().split()
        result_address = result.get('display_name', '').lower()
        
        matches = sum(1 for part in address_parts if part in result_address)
        confidence = matches / len(address_parts) if address_parts else 0.0
        
        # Boost confidence if it's in Illinois
        if 'illinois' in result_address or 'il' in result_address:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_here_confidence(self, item: Dict, original_address: str) -> float:
        """Calculate confidence score for Here API results."""
        # Here API provides scoring
        score = item.get('scoring', {}).get('queryScore', 0.0)
        return min(score / 100.0, 1.0)
    
    def discover_illinois_jails(self, county: str = None) -> List[IllinoisJail]:
        """
        Discover jail facilities in Illinois using web scraping and geocoding.
        
        Args:
            county: Specific county to search (if None, searches all counties)
            
        Returns:
            List of discovered jail facilities
        """
        jails = []
        
        # This is a placeholder for the discovery logic
        # In a real implementation, you would:
        # 1. Scrape county sheriff websites
        # 2. Search for municipal police departments
        # 3. Query state databases
        # 4. Use OSM data to find correctional facilities
        
        print(f"🔍 Discovering jail facilities in Illinois...")
        if county:
            print(f"   Focusing on {county} County")
        else:
            print(f"   Searching all {len(ILLINOIS_COUNTIES)} counties")
        
        # For now, return a basic structure
        # In production, this would be much more comprehensive
        return jails
    
    def geocode_jail_addresses(self, jails: List[IllinoisJail], 
                             use_here: bool = False, here_api_key: str = None) -> List[IllinoisJail]:
        """
        Geocode a list of jail addresses.
        
        Args:
            jails: List of jail facilities to geocode
            use_here: Whether to use Here API
            here_api_key: Here API key if using Here API
            
        Returns:
            List of jails with geocoding information
        """
        geocoded_jails = []
        
        for i, jail in enumerate(jails):
            print(f"   Geocoding {i+1}/{len(jails)}: {jail.name}")
            
            # Try Nominatim first (free)
            geocoded = self.geocode_with_nominatim(jail.address)
            
            # Try Here API if Nominatim failed and Here is available
            if not geocoded and use_here and here_api_key:
                geocoded = self.geocode_with_here(jail.address, here_api_key)
            
            if geocoded:
                jail.latitude = geocoded['latitude']
                jail.longitude = geocoded['longitude']
                print(f"     ✅ {geocoded['latitude']:.4f}, {geocoded['longitude']:.4f} (confidence: {geocoded['confidence']:.2f})")
            else:
                print(f"     ❌ Failed to geocode")
            
            geocoded_jails.append(jail)
        
        # Save cache
        self._save_cache()
        
        return geocoded_jails
    
    def export_jails_to_parquet(self, jails: List[IllinoisJail], output_path: Path):
        """Export jails to Parquet file."""
        data = []
        for jail in jails:
            data.append({
                'name': jail.name,
                'official_name': jail.official_name,
                'address': jail.address,
                'city': jail.city,
                'county': jail.county,
                'state': jail.state,
                'zip_code': jail.zip_code,
                'latitude': jail.latitude,
                'longitude': jail.longitude,
                'facility_type': jail.facility_type,
                'phone': jail.phone,
                'capacity': jail.capacity,
                'status': jail.status
            })
        
        df = pl.DataFrame(data)
        df.write_parquet(output_path)
        print(f"💾 Exported {len(jails)} jail facilities to {output_path}")

def create_illinois_jail_database(output_path: Path = Path("illinois_jails_database.parquet")):
    """
    Create a comprehensive Illinois jail database.
    
    This function would:
    1. Discover all Illinois correctional facilities
    2. Geocode their addresses
    3. Export to Parquet file
    
    Args:
        output_path: Path to save the database
    """
    geocoder = IllinoisJailGeocoder()
    
    # Discover jails (this would be implemented with actual discovery logic)
    jails = geocoder.discover_illinois_jails()
    
    # Geocode addresses
    geocoded_jails = geocoder.geocode_jail_addresses(jails)
    
    # Export to file
    geocoder.export_jails_to_parquet(geocoded_jails, output_path)
    
    return geocoded_jails
