"""
Unified Illinois Jail Geocoding Processor
Combines Illinois database building with existing data matching.
"""

import polars as pl
from pathlib import Path
from typing import Dict, Optional
from .illinois_database_builder import IllinoisJailDatabaseBuilder
from .address_geocoder import IllinoisAddressGeocoder

class UnifiedIllinoisJailProcessor:
    """
    Unified processor that:
    1. Builds Illinois jail database from official sources
    2. Geocodes with OSM
    3. Matches with your existing data
    4. Creates unified database for dashboard
    """
    
    def __init__(self, cache_dir: str = "illinois_jail_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.builder = IllinoisJailDatabaseBuilder(cache_dir)
        self.geocoder = IllinoisAddressGeocoder()
    
    def process_all_data(self, existing_data_path: Path) -> Dict[str, pl.DataFrame]:
        """
        Process all data: build Illinois DB, match with existing data.
        
        Args:
            existing_data_path: Path to existing jail events data
            
        Returns:
            Dictionary with processed dataframes
        """
        print("🚀 Starting Unified Illinois Jail Processing")
        print("=" * 60)
        
        # Step 1: Build Illinois jail database
        print("\n📋 Step 1: Building Illinois Jail Database")
        illinois_db = self._get_or_build_illinois_database()
        
        # Step 2: Load existing data
        print("\n📂 Step 2: Loading Existing Data")
        existing_data = self._load_existing_data(existing_data_path)
        
        # Step 3: Match existing data with Illinois database
        print("\n🔗 Step 3: Matching Data")
        matched_data = self.builder.match_with_existing_data(illinois_db, existing_data)
        
        # Step 4: Create unified database
        print("\n🗄️ Step 4: Creating Unified Database")
        unified_db = self._create_unified_database(illinois_db, matched_data)
        
        # Step 5: Export results
        print("\n💾 Step 5: Exporting Results")
        self._export_results(illinois_db, matched_data, unified_db)
        
        # Step 6: Generate statistics
        print("\n📊 Step 6: Generating Statistics")
        stats = self._generate_statistics(illinois_db, matched_data, unified_db)
        
        return {
            'illinois_database': illinois_db,
            'matched_data': matched_data,
            'unified_database': unified_db,
            'statistics': stats
        }
    
    def _get_or_build_illinois_database(self) -> pl.DataFrame:
        """Get existing Illinois database or build new one."""
        db_path = self.cache_dir / "illinois_jails_database.parquet"
        
        if db_path.exists():
            print(f"   ✅ Loading existing Illinois database from {db_path}")
            return pl.read_parquet(db_path)
        else:
            print("   🔨 Building new Illinois database...")
            return self.builder.build_comprehensive_database()
    
    def _load_existing_data(self, data_path: Path) -> pl.DataFrame:
        """Load existing jail events data."""
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        print(f"   📂 Loading data from {data_path}")
        
        if data_path.suffix == '.xlsx':
            df = pl.read_excel(data_path)
        elif data_path.suffix == '.parquet':
            df = pl.read_parquet(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")
        
        print(f"   📊 Loaded {len(df)} records")
        return df
    
    def _create_unified_database(self, illinois_db: pl.DataFrame, 
                                matched_data: pl.DataFrame) -> pl.DataFrame:
        """Create unified database combining Illinois DB with matched data."""
        print("   🔄 Creating unified database...")
        
        # Add source information
        illinois_db_with_source = illinois_db.with_columns([
            pl.lit("illinois_database").alias("data_source")
        ])
        
        # For matched data, we need to align columns with Illinois DB
        # Create a standardized matched data structure
        matched_standardized = self._standardize_matched_data(matched_data)
        matched_data_with_source = matched_standardized.with_columns([
            pl.lit("jail_events").alias("data_source")
        ])
        
        # Combine the data
        unified = pl.concat([illinois_db_with_source, matched_data_with_source])
        
        print(f"   📊 Unified database: {len(unified)} total records")
        return unified
    
    def _standardize_matched_data(self, matched_data: pl.DataFrame) -> pl.DataFrame:
        """Standardize matched data to match Illinois DB structure."""
        # Illinois DB columns: ['name', 'official_name', 'address', 'city', 'county', 'facility_type', 'phone', 'capacity', 'latitude', 'longitude', 'geocoded_confidence', 'geocoded_method', 'geocoded_formatted_address', 'status']
        
        # Create standardized DataFrame with exact same columns as Illinois DB
        standardized_data = []
        
        for row in matched_data.iter_rows(named=True):
            standardized_row = {
                'name': row.get('Cleaned Facility Name', ''),
                'official_name': row.get('Cleaned Facility Name', ''),
                'address': row.get('Cleaned Address', ''),
                'city': None,  # Will be extracted later
                'county': None,  # Will be extracted later
                'facility_type': 'unknown',  # Will be classified later
                'phone': None,
                'capacity': None,
                'latitude': row.get('illinois_latitude'),
                'longitude': row.get('illinois_longitude'),
                'geocoded_confidence': row.get('match_confidence', 0.0),
                'geocoded_method': row.get('match_method', 'unknown'),
                'geocoded_formatted_address': None,
                'status': 'matched'
            }
            
            standardized_data.append(standardized_row)
        
        return pl.DataFrame(standardized_data)
    
    def _export_results(self, illinois_db: pl.DataFrame, 
                       matched_data: pl.DataFrame, 
                       unified_db: pl.DataFrame):
        """Export all results to files."""
        output_dir = Path("data/illinois_jail_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export Illinois database
        illinois_path = output_dir / "illinois_jails_database.parquet"
        illinois_db.write_parquet(illinois_path)
        print(f"   💾 Illinois database: {illinois_path}")
        
        # Export matched data
        matched_path = output_dir / "jail_events_with_coordinates.parquet"
        matched_data.write_parquet(matched_path)
        print(f"   💾 Matched data: {matched_path}")
        
        # Export unified database
        unified_path = output_dir / "unified_illinois_jails.parquet"
        unified_db.write_parquet(unified_path)
        print(f"   💾 Unified database: {unified_path}")
        
        # Export Excel for dashboard
        excel_path = output_dir / "illinois_jails_for_dashboard.xlsx"
        self._export_to_excel(unified_db, excel_path)
        print(f"   📊 Dashboard Excel: {excel_path}")
    
    def _export_to_excel(self, df: pl.DataFrame, excel_path: Path):
        """Export to Excel with proper formatting for dashboard."""
        # Select relevant columns for dashboard
        dashboard_columns = [
            'name', 'official_name', 'address', 'city', 'county', 'state',
            'facility_type', 'latitude', 'longitude', 'geocoded_confidence',
            'phone', 'capacity', 'data_source'
        ]
        
        # Filter columns that exist
        available_columns = [col for col in dashboard_columns if col in df.columns]
        dashboard_df = df.select(available_columns)
        
        # Write to Excel
        dashboard_df.write_excel(excel_path)
    
    def _generate_statistics(self, illinois_db: pl.DataFrame, 
                           matched_data: pl.DataFrame, 
                           unified_db: pl.DataFrame) -> Dict:
        """Generate comprehensive statistics."""
        stats = {
            'illinois_database': {
                'total_facilities': len(illinois_db),
                'geocoded_facilities': len(illinois_db.filter(pl.col('latitude').is_not_null())),
                'county_jails': len(illinois_db.filter(pl.col('facility_type') == 'county')),
                'municipal_jails': len(illinois_db.filter(pl.col('facility_type') == 'municipal')),
                'juvenile_facilities': len(illinois_db.filter(pl.col('facility_type') == 'juvenile'))
            },
            'matched_data': {
                'total_records': len(matched_data),
                'successfully_matched': len(matched_data.filter(pl.col('illinois_latitude').is_not_null())),
                'match_rate': len(matched_data.filter(pl.col('illinois_latitude').is_not_null())) / len(matched_data) if len(matched_data) > 0 else 0
            },
            'unified_database': {
                'total_records': len(unified_db),
                'unique_facilities': len(unified_db['name'].unique()),
                'counties_covered': len(unified_db['county'].unique())
            }
        }
        
        # Print statistics
        print(f"\n📊 Processing Statistics:")
        print(f"   Illinois Database: {stats['illinois_database']['total_facilities']} facilities")
        print(f"   Geocoded: {stats['illinois_database']['geocoded_facilities']} ({stats['illinois_database']['geocoded_facilities']/stats['illinois_database']['total_facilities']*100:.1f}%)")
        print(f"   County Jails: {stats['illinois_database']['county_jails']}")
        print(f"   Municipal Jails: {stats['illinois_database']['municipal_jails']}")
        print(f"   Juvenile Facilities: {stats['illinois_database']['juvenile_facilities']}")
        print(f"\n   Matched Data: {stats['matched_data']['total_records']} records")
        print(f"   Successfully Matched: {stats['matched_data']['successfully_matched']} ({stats['matched_data']['match_rate']*100:.1f}%)")
        print(f"\n   Unified Database: {stats['unified_database']['total_records']} total records")
        print(f"   Unique Facilities: {stats['unified_database']['unique_facilities']}")
        print(f"   Counties Covered: {stats['unified_database']['counties_covered']}")
        
        return stats

def process_illinois_jail_data(existing_data_path: str = "data/jails-data/output/jails_database_with_links.xlsx"):
    """
    Main function to process all Illinois jail data.
    
    Args:
        existing_data_path: Path to existing jail events data
    """
    processor = UnifiedIllinoisJailProcessor()
    results = processor.process_all_data(Path(existing_data_path))
    return results

if __name__ == "__main__":
    # Process all data
    results = process_illinois_jail_data()
    print("\n🎉 Illinois jail data processing completed!")
    print("Check the 'data/illinois_jail_analysis' directory for results.")
