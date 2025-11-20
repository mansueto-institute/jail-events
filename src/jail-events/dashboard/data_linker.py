"""
Data Linker for Illinois Jail Dashboard
Links jail records from jails_pdfs_full.parquet with geocoded Illinois jail database.
"""

import polars as pl
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import jellyfish
from datetime import datetime
import re

class JailDataLinker:
    """
    Links jail event records with geocoded Illinois jail facilities.
    """
    
    def __init__(self, 
                 jail_records_path: str = None,
                 geocoded_db_path: str = None):
        # Set default paths if not provided - relative to script location
        base_dir = Path(__file__).parent.parent  # Points to src/jail-events/
        
        if jail_records_path is None:
            jail_records_path = base_dir / "data/jails-data/output/jails_pdfs_cleaned.parquet"
        if geocoded_db_path is None:
            geocoded_db_path = base_dir / "data/illinois_jail_analysis/unified_illinois_jails.parquet"
        
        self.jail_records_path = Path(jail_records_path)
        self.geocoded_db_path = Path(geocoded_db_path)
        self.jail_records_df: Optional[pl.DataFrame] = None
        self.geocoded_db_df: Optional[pl.DataFrame] = None
        self.linked_data_df: Optional[pl.DataFrame] = None
        
    def load_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Load both jail records and geocoded database."""
        print("📂 Loading jail records and geocoded database...")
        
        # Load jail records
        if not self.jail_records_path.exists():
            raise FileNotFoundError(f"Jail records not found: {self.jail_records_path}")
        
        self.jail_records_df = pl.read_parquet(self.jail_records_path)
        print(f"   📊 Loaded {len(self.jail_records_df)} jail records")
        
        # Load geocoded database
        if not self.geocoded_db_path.exists():
            raise FileNotFoundError(f"Geocoded database not found: {self.geocoded_db_path}")
        
        self.geocoded_db_df = pl.read_parquet(self.geocoded_db_path)
        print(f"   📍 Loaded {len(self.geocoded_db_df)} geocoded facilities")
        
        return self.jail_records_df, self.geocoded_db_df
    
    def clean_facility_name(self, name: str) -> str:
        """Clean facility name for better matching."""
        if not isinstance(name, str):
            return ""
        
        # Convert to lowercase and remove extra spaces
        cleaned = name.lower().strip()
        
        # Remove common suffixes
        suffixes_to_remove = [
            " jail", " detention center", " detention facility", 
            " adult detention", " correctional facility", " county jail",
            " police department", " pd", " sheriff's office", " sheriff",
            " department of corrections", " doc"
        ]
        
        for suffix in suffixes_to_remove:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "the ", "a ", "an "
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned
    
    def extract_county_from_address(self, address: str) -> Optional[str]:
        """Extract county name from address string."""
        if not isinstance(address, str):
            return None
        
        # Look for "County" in the address
        county_match = re.search(r'([A-Za-z\s]+)\s+County', address, re.IGNORECASE)
        if county_match:
            return county_match.group(1).strip().title()
        
        return None
    
    def match_facilities(self, 
                        similarity_threshold: float = 0.7,
                        county_boost: float = 0.1) -> pl.DataFrame:
        """
        Match jail records to geocoded facilities using fuzzy matching.
        
        Args:
            similarity_threshold: Minimum similarity score for a match
            county_boost: Additional score boost for county matches
        """
        if self.jail_records_df is None or self.geocoded_db_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print("🔗 Matching jail records to geocoded facilities...")
        
        # Prepare geocoded database for matching
        geocoded_clean = self.geocoded_db_df.with_columns([
            pl.col("name").map_elements(self.clean_facility_name, return_dtype=pl.String).alias("cleaned_name"),
            pl.col("county").alias("geocoded_county")
        ]).filter(pl.col("latitude").is_not_null())
        
        # Prepare jail records for matching
        jail_clean = self.jail_records_df.with_columns([
            pl.col("Facility Name").map_elements(self.clean_facility_name, return_dtype=pl.String).alias("cleaned_facility_name"),
            pl.col("Address").map_elements(self.extract_county_from_address, return_dtype=pl.String).alias("extracted_county")
        ])
        
        matched_records = []
        total_records = len(jail_clean)
        
        for i, jail_row in enumerate(jail_clean.iter_rows(named=True)):
            if i % 1000 == 0:
                print(f"   Processing record {i+1}/{total_records}")
            
            best_match = None
            best_score = 0.0
            best_geocoded_row = None
            
            jail_facility = jail_row.get("cleaned_facility_name", "")
            jail_county = jail_row.get("extracted_county", "")
            
            # Try to match with geocoded facilities
            for geocoded_row in geocoded_clean.iter_rows(named=True):
                geocoded_facility = geocoded_row.get("cleaned_name", "")
                geocoded_county = geocoded_row.get("geocoded_county", "")
                
                # Calculate base similarity
                base_similarity = jellyfish.jaro_winkler_similarity(jail_facility, geocoded_facility)
                
                # Add county boost if counties match
                county_boost_score = 0.0
                if jail_county and geocoded_county:
                    county_similarity = jellyfish.jaro_winkler_similarity(
                        jail_county.lower(), 
                        geocoded_county.lower()
                    )
                    if county_similarity > 0.8:  # Counties match
                        county_boost_score = county_boost
                
                total_score = base_similarity + county_boost_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_match = geocoded_facility
                    best_geocoded_row = geocoded_row
            
            # Create matched record
            matched_record = dict(jail_row)
            
            if best_score >= similarity_threshold and best_geocoded_row:
                # Add geocoded information
                matched_record.update({
                    "matched_facility_name": best_geocoded_row.get("name", ""),
                    "matched_latitude": best_geocoded_row.get("latitude"),
                    "matched_longitude": best_geocoded_row.get("longitude"),
                    "matched_county": best_geocoded_row.get("county", ""),
                    "matched_facility_type": best_geocoded_row.get("facility_type", ""),
                    "match_confidence": best_score,
                    "match_method": "fuzzy_match"
                })
                print(f"   ✅ Matched: {jail_facility} -> {best_match} (score: {best_score:.3f})")
            else:
                # No match found
                matched_record.update({
                    "matched_facility_name": None,
                    "matched_latitude": None,
                    "matched_longitude": None,
                    "matched_county": None,
                    "matched_facility_type": None,
                    "match_confidence": 0.0,
                    "match_method": "no_match"
                })
                print(f"   ❌ No match: {jail_facility} (best score: {best_score:.3f})")
            
            matched_records.append(matched_record)
        
        self.linked_data_df = pl.DataFrame(matched_records)
        
        # Calculate matching statistics
        matched_count = len(self.linked_data_df.filter(pl.col("match_confidence") > 0))
        match_rate = matched_count / total_records * 100
        
        print(f"\n📊 Matching Results:")
        print(f"   Total Records: {total_records}")
        print(f"   Successfully Matched: {matched_count}")
        print(f"   Match Rate: {match_rate:.1f}%")
        
        return self.linked_data_df
    
    def get_matching_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the matching process."""
        if self.linked_data_df is None:
            return {}
        
        total_records = len(self.linked_data_df)
        matched_records = self.linked_data_df.filter(pl.col("match_confidence") > 0)
        matched_count = len(matched_records)
        
        # Match rate by confidence level
        high_confidence = len(matched_records.filter(pl.col("match_confidence") >= 0.9))
        medium_confidence = len(matched_records.filter((pl.col("match_confidence") >= 0.7) & (pl.col("match_confidence") < 0.9)))
        low_confidence = len(matched_records.filter(pl.col("match_confidence") < 0.7))
        
        # Match rate by facility type
        facility_type_matches = matched_records.group_by("matched_facility_type").len().sort("len", descending=True)
        
        # Match rate by county
        county_matches = matched_records.group_by("matched_county").len().sort("len", descending=True)
        
        return {
            "total_records": total_records,
            "matched_records": matched_count,
            "match_rate": matched_count / total_records * 100,
            "high_confidence_matches": high_confidence,
            "medium_confidence_matches": medium_confidence,
            "low_confidence_matches": low_confidence,
            "facility_type_matches": facility_type_matches.to_dicts(),
            "county_matches": county_matches.to_dicts()
        }
    
    def export_linked_data(self, output_path: str = None) -> str:
        """Export the linked data to a parquet file."""
        if self.linked_data_df is None:
            raise ValueError("No linked data available. Run match_facilities() first.")
        
        if output_path is None:
            base_dir = Path(__file__).parent.parent  # Points to src/jail-events/
            output_path = base_dir / "data/illinois_jail_analysis/linked_jail_data.parquet"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.linked_data_df.write_parquet(output_path)
        print(f"💾 Linked data exported to: {output_path}")
        
        return str(output_path)

def link_jail_data():
    """Main function to link jail data with geocoded facilities."""
    print("🔗 Illinois Jail Data Linking")
    print("=" * 40)
    
    # Initialize linker
    linker = JailDataLinker()
    
    # Load data
    jail_records, geocoded_db = linker.load_data()
    
    # Match facilities
    linked_data = linker.match_facilities()
    
    # Get statistics
    stats = linker.get_matching_statistics()
    
    print(f"\n📈 Detailed Statistics:")
    print(f"   High Confidence (≥0.9): {stats['high_confidence_matches']}")
    print(f"   Medium Confidence (0.7-0.9): {stats['medium_confidence_matches']}")
    print(f"   Low Confidence (<0.7): {stats['low_confidence_matches']}")
    
    print(f"\n🏛️ Top Matched Facility Types:")
    for item in stats['facility_type_matches'][:5]:
        print(f"   {item['matched_facility_type']}: {item['len']}")
    
    print(f"\n🏘️ Top Matched Counties:")
    for item in stats['county_matches'][:5]:
        if item['matched_county']:
            print(f"   {item['matched_county']}: {item['len']}")
    
    # Export linked data
    output_path = linker.export_linked_data()
    
    return linker, linked_data, stats

if __name__ == "__main__":
    linker, linked_data, stats = link_jail_data()
    print("\n🎉 Data linking completed successfully!")
