"""
Advanced address geocoding system for Illinois jail addresses.
Uses multiple geocoding services and builds a comprehensive database.
"""

import polars as pl
import requests
import time
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
from .address_cleaner import clean_address, calculate_address_similarity

class IllinoisAddressGeocoder:
    """Advanced geocoder for Illinois jail addresses."""
    
    def __init__(self, cache_file: str = "geocoding_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Illinois Jail Geocoder/1.0 (Educational Research)'
        })
        
        # Illinois-specific patterns for better geocoding
        self.illinois_patterns = {
            'county_jail': r'(county|sheriff).*jail',
            'municipal_jail': r'(city|municipal|police).*jail',
            'detention_center': r'detention.*center',
            'correctional_facility': r'correctional.*facility'
        }
    
    def _load_cache(self) -> Dict:
        """Load geocoding cache."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save geocoding cache."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def geocode_with_nominatim(self, address: str, context: str = "Illinois") -> Optional[Dict]:
        """
        Geocode using OpenStreetMap Nominatim API.
        
        Args:
            address: Address to geocode
            context: Additional context for better results
            
        Returns:
            Geocoding result or None
        """
        if not address:
            return None
        
        # Check cache
        cache_key = f"nominatim_{address}_{context}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Clean and prepare address
            cleaned_address = clean_address(address)
            query = f"{cleaned_address}, {context}, USA"
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'addressdetails': 1,
                'limit': 1,
                'countrycodes': 'us'
            }
            
            # Rate limiting
            time.sleep(1.1)  # Nominatim allows 1 request per second
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                geocoded = {
                    'latitude': float(result['lat']),
                    'longitude': float(result['lon']),
                    'formatted_address': result.get('display_name', ''),
                    'confidence': self._calculate_nominatim_confidence(result, address),
                    'source': 'nominatim',
                    'address_components': result.get('address', {}),
                    'place_id': result.get('place_id'),
                    'osm_type': result.get('osm_type'),
                    'osm_id': result.get('osm_id')
                }
                
                # Cache result
                self.cache[cache_key] = geocoded
                return geocoded
                
        except Exception as e:
            print(f"Error geocoding with Nominatim: {e}")
        
        return None
    
    def geocode_with_here(self, address: str, api_key: str) -> Optional[Dict]:
        """
        Geocode using Here API.
        
        Args:
            address: Address to geocode
            api_key: Here API key
            
        Returns:
            Geocoding result or None
        """
        if not address or not api_key:
            return None
        
        # Check cache
        cache_key = f"here_{address}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            cleaned_address = clean_address(address)
            
            url = "https://geocode.search.hereapi.com/v1/geocode"
            params = {
                'q': cleaned_address,
                'apikey': api_key,
                'in': 'countryCode:USA,stateCode:IL'
            }
            
            response = self.session.get(url, params=params, timeout=15)
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
                    'source': 'here',
                    'address_components': item.get('address', {}),
                    'id': item.get('id')
                }
                
                # Cache result
                self.cache[cache_key] = geocoded
                return geocoded
                
        except Exception as e:
            print(f"Error geocoding with Here API: {e}")
        
        return None
    
    def _calculate_nominatim_confidence(self, result: Dict, original_address: str) -> float:
        """Calculate confidence score for Nominatim results."""
        confidence = 0.0
        
        # Base confidence from address matching
        original_lower = original_address.lower()
        result_address = result.get('display_name', '').lower()
        
        # Check for key components
        address_parts = re.findall(r'\b\w+\b', original_lower)
        matches = sum(1 for part in address_parts if part in result_address)
        if address_parts:
            confidence += (matches / len(address_parts)) * 0.6
        
        # Boost if it's in Illinois
        if 'illinois' in result_address or 'il' in result_address:
            confidence += 0.2
        
        # Boost if it's a correctional facility
        if any(term in result_address for term in ['jail', 'prison', 'correctional', 'detention']):
            confidence += 0.1
        
        # Boost if address components match
        address_components = result.get('address', {})
        if 'county' in address_components and 'county' in original_lower:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_here_confidence(self, item: Dict, original_address: str) -> float:
        """Calculate confidence score for Here API results."""
        scoring = item.get('scoring', {})
        query_score = scoring.get('queryScore', 0.0)
        field_score = scoring.get('fieldScore', {})
        
        # Convert Here's 0-100 scale to 0-1
        base_confidence = query_score / 100.0
        
        # Boost confidence based on field scores
        if 'city' in field_score:
            base_confidence += field_score['city'] / 100.0 * 0.2
        
        if 'street' in field_score:
            base_confidence += field_score['street'] / 100.0 * 0.3
        
        return min(base_confidence, 1.0)
    
    def geocode_dataframe(self, df: pl.DataFrame, 
                         address_col: str = "Cleaned Address",
                         facility_col: str = "Cleaned Facility Name",
                         use_here: bool = False,
                         here_api_key: str = None) -> pl.DataFrame:
        """
        Geocode all addresses in a DataFrame.
        
        Args:
            df: DataFrame with addresses
            address_col: Column name containing addresses
            facility_col: Column name containing facility names
            use_here: Whether to use Here API
            here_api_key: Here API key if using Here API
            
        Returns:
            DataFrame with geocoding results
        """
        print(f"🌍 Geocoding {len(df)} addresses...")
        
        results = []
        successful = 0
        failed = 0
        
        for i, row in enumerate(df.iter_rows(named=True)):
            address = row.get(address_col, "")
            facility = row.get(facility_col, "")
            
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(df)} ({i/len(df)*100:.1f}%)")
            
            # Try Nominatim first
            geocoded = self.geocode_with_nominatim(address)
            
            # Try Here API if Nominatim failed
            if not geocoded and use_here and here_api_key:
                geocoded = self.geocode_with_here(address, here_api_key)
            
            if geocoded:
                successful += 1
                row.update({
                    'geocoded_latitude': geocoded['latitude'],
                    'geocoded_longitude': geocoded['longitude'],
                    'geocoded_confidence': geocoded['confidence'],
                    'geocoded_method': geocoded['source'],
                    'geocoded_formatted_address': geocoded['formatted_address'],
                    'geocoded_place_id': geocoded.get('place_id', ''),
                    'geocoded_osm_type': geocoded.get('osm_type', ''),
                    'geocoded_osm_id': geocoded.get('osm_id', '')
                })
            else:
                failed += 1
                row.update({
                    'geocoded_latitude': None,
                    'geocoded_longitude': None,
                    'geocoded_confidence': 0.0,
                    'geocoded_method': 'failed',
                    'geocoded_formatted_address': '',
                    'geocoded_place_id': '',
                    'geocoded_osm_type': '',
                    'geocoded_osm_id': ''
                })
            
            results.append(row)
        
        # Save cache
        self._save_cache()
        
        print(f"✅ Geocoding completed: {successful} successful, {failed} failed")
        
        return pl.DataFrame(results)
    
    def build_illinois_jail_database(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Build a comprehensive Illinois jail database from geocoded data.
        
        Args:
            df: DataFrame with geocoded jail data
            
        Returns:
            Enhanced DataFrame with Illinois jail database information
        """
        print("🏛️ Building Illinois jail database...")
        
        # Add facility type classification
        df_classified = df.with_columns([
            pl.col("Cleaned Facility Name").map_elements(
                self._classify_facility_type, return_dtype=pl.String
            ).alias("facility_type")
        ])
        
        # Add county information
        df_with_county = df_classified.with_columns([
            pl.col("geocoded_formatted_address").map_elements(
                self._extract_county, return_dtype=pl.String
            ).alias("geocoded_county")
        ])
        
        # Add confidence categories
        df_with_confidence = df_with_county.with_columns([
            pl.when(pl.col("geocoded_confidence") >= 0.9)
            .then(pl.lit("high"))
            .when(pl.col("geocoded_confidence") >= 0.7)
            .then(pl.lit("medium"))
            .when(pl.col("geocoded_confidence") >= 0.5)
            .then(pl.lit("low"))
            .otherwise(pl.lit("very_low"))
            .alias("confidence_category")
        ])
        
        return df_with_confidence
    
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
    
    def _extract_county(self, formatted_address: str) -> str:
        """Extract county from formatted address."""
        if not formatted_address:
            return ""
        
        # Look for county patterns
        county_match = re.search(r'(\w+ County)', formatted_address)
        if county_match:
            return county_match.group(1)
        
        return ""
    
    def get_geocoding_statistics(self, df: pl.DataFrame) -> Dict:
        """Get comprehensive geocoding statistics."""
        if 'geocoded_confidence' not in df.columns:
            return {}
        
        total = len(df)
        successful = len(df.filter(pl.col('geocoded_confidence') > 0))
        high_confidence = len(df.filter(pl.col('geocoded_confidence') >= 0.8))
        
        # Method breakdown
        method_counts = df['geocoded_method'].value_counts().to_dict() if 'geocoded_method' in df.columns else {}
        
        # Facility type breakdown
        facility_type_counts = df['facility_type'].value_counts().to_dict() if 'facility_type' in df.columns else {}
        
        # County breakdown
        county_counts = df['geocoded_county'].value_counts().to_dict() if 'geocoded_county' in df.columns else {}
        
        return {
            'total_addresses': total,
            'successfully_geocoded': successful,
            'success_rate': successful / total if total > 0 else 0,
            'high_confidence_matches': high_confidence,
            'high_confidence_rate': high_confidence / total if total > 0 else 0,
            'methods_used': method_counts,
            'facility_types': facility_type_counts,
            'counties': county_counts,
            'average_confidence': df['geocoded_confidence'].mean() if 'geocoded_confidence' in df.columns else 0
        }
