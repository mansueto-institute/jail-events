"""
Main geocoding processor for jail addresses.
"""

import polars as pl
from typing import Dict, Optional
from pathlib import Path
from .address_geocoder import IllinoisAddressGeocoder
from .address_clusterer import AddressClusterer
from .address_cleaner import clean_address

class JailAddressProcessor:
    """Main processor for geocoding jail addresses."""
    
    def __init__(self, similarity_threshold: float = 0.8, use_here_api: bool = False, here_api_key: str = None):
        self.geocoder = IllinoisAddressGeocoder()
        self.clusterer = AddressClusterer(similarity_threshold=similarity_threshold)
        self.use_here_api = use_here_api
        self.here_api_key = here_api_key
    
    def process_jail_addresses(self, df: pl.DataFrame, 
                             address_col: str = "Cleaned Address",
                             facility_col: str = "Cleaned Facility Name") -> pl.DataFrame:
        """
        Process jail addresses with cleaning, clustering, and geocoding.
        
        Args:
            df: DataFrame with jail data
            address_col: Column name containing addresses
            facility_col: Column name containing facility names
            
        Returns:
            DataFrame with geocoding results
        """
        print("Processing jail addresses for geocoding...")
        
        # Step 1: Clean addresses
        print("  - Cleaning addresses...")
        df_cleaned = df.with_columns([
            pl.col(address_col).map_elements(clean_address, return_dtype=pl.String).alias("cleaned_address")
        ])
        
        # Step 2: Cluster similar addresses
        print("  - Clustering similar addresses...")
        df_clustered = self.clusterer.cluster_addresses(df_cleaned, "cleaned_address")
        
        # Step 3: Suggest corrections
        print("  - Suggesting address corrections...")
        df_with_suggestions = self.clusterer.suggest_address_corrections(df_clustered, "cleaned_address")
        
        # Step 4: Geocode addresses
        print("  - Geocoding addresses...")
        df_geocoded = self.geocoder.geocode_dataframe(
            df_with_suggestions, 
            "cleaned_address", 
            facility_col,
            use_here=self.use_here_api,
            here_api_key=self.here_api_key
        )
        
        # Step 5: Build Illinois jail database
        print("  - Building Illinois jail database...")
        df_final = self.geocoder.build_illinois_jail_database(df_geocoded)
        
        print("Address processing completed!")
        return df_final
    
    def _add_distance_calculations(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add distance calculations between geocoded points."""
        # This would calculate distances between points
        # For now, just return the dataframe as-is
        return df
    
    def get_processing_stats(self, df: pl.DataFrame) -> Dict:
        """Get comprehensive statistics about the processing results."""
        stats = {}
        
        # Geocoding stats
        geocoding_stats = self.geocoder.get_geocoding_statistics(df)
        stats.update(geocoding_stats)
        
        # Clustering stats
        clustering_stats = self.clusterer.get_cluster_summary(df, "cleaned_address")
        stats.update(clustering_stats)
        
        # Address quality stats
        if 'suggestion_confidence' in df.columns:
            high_confidence_suggestions = len(df.filter(pl.col('suggestion_confidence') >= 0.8))
            stats['high_confidence_suggestions'] = high_confidence_suggestions
            stats['suggestion_rate'] = high_confidence_suggestions / len(df) if len(df) > 0 else 0
        
        return stats
    
    def export_geocoded_data(self, df: pl.DataFrame, output_path: Path) -> None:
        """Export geocoded data to a file."""
        print(f"Exporting geocoded data to: {output_path}")
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to parquet
        df.write_parquet(output_path)
        
        # Also create a summary report
        summary_path = output_path.parent / f"{output_path.stem}_summary.txt"
        self._create_summary_report(df, summary_path)
        
        print(f"Data exported successfully!")
        print(f"   - Main file: {output_path}")
        print(f"   - Summary: {summary_path}")
    
    def _create_summary_report(self, df: pl.DataFrame, summary_path: Path) -> None:
        """Create a summary report of the geocoding results."""
        stats = self.get_processing_stats(df)
        
        with open(summary_path, 'w') as f:
            f.write("Jail Address Geocoding Summary Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Addresses Processed: {stats.get('total_addresses', 0)}\n")
            f.write(f"Successfully Geocoded: {stats.get('successfully_geocoded', 0)}\n")
            f.write(f"Success Rate: {stats.get('success_rate', 0):.2%}\n")
            f.write(f"High Confidence Matches: {stats.get('high_confidence_matches', 0)}\n")
            f.write(f"High Confidence Rate: {stats.get('high_confidence_rate', 0):.2%}\n\n")
            
            f.write(f"Total Clusters: {stats.get('total_clusters', 0)}\n")
            f.write(f"Largest Cluster Size: {stats.get('largest_cluster_size', 0)}\n")
            f.write(f"Average Cluster Size: {stats.get('average_cluster_size', 0):.2f}\n")
            f.write(f"Clusters with Multiple Addresses: {stats.get('clusters_with_multiple_addresses', 0)}\n\n")
            
            if 'methods_used' in stats:
                f.write("Geocoding Methods Used:\n")
                for method, count in stats['methods_used'].items():
                    f.write(f"  - {method}: {count}\n")
            
            f.write("\nTop Clusters:\n")
            for cluster in stats.get('top_clusters', [])[:5]:
                f.write(f"  - {cluster['address_cluster']}: {cluster['count']} addresses\n")
