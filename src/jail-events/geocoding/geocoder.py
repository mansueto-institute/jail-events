"""
Geocoding utilities for jail addresses using multiple methods.
"""

import polars as pl
from typing import List, Dict, Optional, Tuple
import requests
import time
from .jail_locations import COOK_COUNTY_JAILS, get_jail_locations_df
from .address_cleaner import clean_address, calculate_address_similarity, find_best_address_match

class JailGeocoder:
    """Geocoder specifically designed for Cook County jail addresses."""
    
    def __init__(self, use_cached: bool = True):
        self.use_cached = use_cached
        self.known_jails = get_jail_locations_df()
        self.cache = {}
        
    def geocode_address(self, address: str, facility_name: str = "") -> Optional[Dict]:
        """
        Geocode a jail address using multiple methods.
        
        Args:
            address: Address to geocode
            facility_name: Name of the facility (optional)
            
        Returns:
            Dictionary with geocoding results or None
        """
        if not address or address.strip() == "":
            return None
            
        # Check cache first
        if self.use_cached and address in self.cache:
            return self.cache[address]
        
        # Method 1: Try to match against known jail locations
        known_match = self._match_known_jail(address, facility_name)
        if known_match:
            result = {
                'address': address,
                'matched_address': known_match['address'],
                'latitude': known_match['latitude'],
                'longitude': known_match['longitude'],
                'confidence': known_match['confidence'],
                'method': 'known_jail_match',
                'facility_name': known_match['jail_name'],
                'facility_type': known_match['facility_type']
            }
            if self.use_cached:
                self.cache[address] = result
            return result
        
        # Method 2: Use external geocoding service (if available)
        external_result = self._geocode_external(address)
        if external_result:
            if self.use_cached:
                self.cache[address] = external_result
            return external_result
        
        # Method 3: Fuzzy matching with known addresses
        fuzzy_match = self._fuzzy_match_address(address)
        if fuzzy_match:
            if self.use_cached:
                self.cache[address] = fuzzy_match
            return fuzzy_match
        
        return None
    
    def _match_known_jail(self, address: str, facility_name: str = "") -> Optional[Dict]:
        """Try to match against known Cook County jail locations."""
        cleaned_address = clean_address(address)
        
        # Get all known addresses
        known_addresses = self.known_jails.select(['address', 'jail_name', 'latitude', 'longitude', 'facility_type']).to_dicts()
        
        # Try exact match first
        for jail in known_addresses:
            if clean_address(jail['address']) == cleaned_address:
                return {
                    'address': jail['address'],
                    'jail_name': jail['jail_name'],
                    'latitude': jail['latitude'],
                    'longitude': jail['longitude'],
                    'facility_type': jail['facility_type'],
                    'confidence': 1.0
                }
        
        # Try fuzzy matching
        best_match = find_best_address_match(address, [j['address'] for j in known_addresses], threshold=0.8)
        if best_match:
            matched_address, confidence = best_match
            for jail in known_addresses:
                if jail['address'] == matched_address:
                    return {
                        'address': jail['address'],
                        'jail_name': jail['jail_name'],
                        'latitude': jail['latitude'],
                        'longitude': jail['longitude'],
                        'facility_type': jail['facility_type'],
                        'confidence': confidence
                    }
        
        return None
    
    def _geocode_external(self, address: str) -> Optional[Dict]:
        """
        Use external geocoding service (placeholder for now).
        In production, you could use Google Maps API, OpenStreetMap, etc.
        """
        # For now, return None to use other methods
        # In production, implement actual geocoding API calls here
        return None
    
    def _fuzzy_match_address(self, address: str) -> Optional[Dict]:
        """Use fuzzy matching to find similar addresses."""
        # This would implement more sophisticated fuzzy matching
        # For now, return None
        return None
    
    def geocode_dataframe(self, df: pl.DataFrame, address_col: str = "Cleaned Address", 
                         facility_col: str = "Cleaned Facility Name") -> pl.DataFrame:
        """
        Geocode all addresses in a DataFrame.
        
        Args:
            df: DataFrame with addresses
            address_col: Column name containing addresses
            facility_col: Column name containing facility names
            
        Returns:
            DataFrame with geocoding results added
        """
        results = []
        
        for row in df.iter_rows(named=True):
            address = row.get(address_col, "")
            facility = row.get(facility_col, "")
            
            geocoded = self.geocode_address(address, facility)
            
            if geocoded:
                row.update({
                    'geocoded_latitude': geocoded['latitude'],
                    'geocoded_longitude': geocoded['longitude'],
                    'geocoded_confidence': geocoded['confidence'],
                    'geocoded_method': geocoded['method'],
                    'geocoded_facility_name': geocoded.get('facility_name', ''),
                    'geocoded_facility_type': geocoded.get('facility_type', ''),
                    'geocoded_matched_address': geocoded.get('matched_address', '')
                })
            else:
                row.update({
                    'geocoded_latitude': None,
                    'geocoded_longitude': None,
                    'geocoded_confidence': 0.0,
                    'geocoded_method': 'no_match',
                    'geocoded_facility_name': '',
                    'geocoded_facility_type': '',
                    'geocoded_matched_address': ''
                })
            
            results.append(row)
        
        return pl.DataFrame(results)
    
    def get_geocoding_stats(self, df: pl.DataFrame) -> Dict:
        """Get statistics about geocoding results."""
        if 'geocoded_confidence' not in df.columns:
            return {}
        
        total = len(df)
        successful = len(df.filter(pl.col('geocoded_confidence') > 0))
        high_confidence = len(df.filter(pl.col('geocoded_confidence') >= 0.8))
        
        return {
            'total_addresses': total,
            'successfully_geocoded': successful,
            'success_rate': successful / total if total > 0 else 0,
            'high_confidence_matches': high_confidence,
            'high_confidence_rate': high_confidence / total if total > 0 else 0,
            'methods_used': df['geocoded_method'].value_counts().to_dict() if 'geocoded_method' in df.columns else {}
        }
