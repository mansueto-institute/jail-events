"""
Address clustering utilities for grouping similar jail addresses.
"""

import polars as pl
from typing import List, Dict, Tuple
from .address_cleaner import cluster_similar_addresses, calculate_address_similarity
from .jail_locations import get_jail_locations_df

class AddressClusterer:
    """Clusters similar jail addresses for better geocoding."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.known_jails = get_jail_locations_df()
    
    def cluster_addresses(self, df: pl.DataFrame, address_col: str = "Cleaned Address") -> pl.DataFrame:
        """
        Cluster similar addresses in a DataFrame.
        
        Args:
            df: DataFrame with addresses
            address_col: Column name containing addresses
            
        Returns:
            DataFrame with cluster information added
        """
        # Get unique addresses
        unique_addresses = df[address_col].unique().to_list()
        
        # Cluster similar addresses
        clusters = cluster_similar_addresses(unique_addresses, self.similarity_threshold)
        
        # Create cluster mapping
        cluster_mapping = {}
        for i, cluster in enumerate(clusters):
            for address in cluster:
                cluster_mapping[address] = f"cluster_{i}"
        
        # Add cluster information to DataFrame
        df_with_clusters = df.with_columns([
            pl.col(address_col).map_elements(
                lambda addr: cluster_mapping.get(addr, "no_cluster"),
                return_dtype=pl.String
            ).alias("address_cluster")
        ])
        
        # Add cluster statistics
        cluster_stats = self._calculate_cluster_stats(clusters)
        df_with_clusters = df_with_clusters.with_columns([
            pl.col("address_cluster").map_elements(
                lambda cluster_id: cluster_stats.get(cluster_id, {}).get('size', 1),
                return_dtype=pl.Int32
            ).alias("cluster_size")
        ])
        
        return df_with_clusters
    
    def _calculate_cluster_stats(self, clusters: List[List[str]]) -> Dict[str, Dict]:
        """Calculate statistics for each cluster."""
        stats = {}
        
        for i, cluster in enumerate(clusters):
            cluster_id = f"cluster_{i}"
            stats[cluster_id] = {
                'size': len(cluster),
                'addresses': cluster,
                'representative_address': self._find_representative_address(cluster)
            }
        
        return stats
    
    def _find_representative_address(self, cluster: List[str]) -> str:
        """Find the most representative address in a cluster."""
        if not cluster:
            return ""
        
        if len(cluster) == 1:
            return cluster[0]
        
        # Find the address that has the highest average similarity to others
        best_address = cluster[0]
        best_avg_similarity = 0.0
        
        for address in cluster:
            similarities = [calculate_address_similarity(address, other) for other in cluster if other != address]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            
            if avg_similarity > best_avg_similarity:
                best_avg_similarity = avg_similarity
                best_address = address
        
        return best_address
    
    def suggest_address_corrections(self, df: pl.DataFrame, address_col: str = "Cleaned Address") -> pl.DataFrame:
        """
        Suggest corrections for addresses based on clustering and known jails.
        
        Args:
            df: DataFrame with addresses
            address_col: Column name containing addresses
            
        Returns:
            DataFrame with suggested corrections
        """
        # Get known jail addresses
        known_addresses = self.known_jails['address'].to_list()
        
        def suggest_correction(address: str) -> Tuple[str, float]:
            """Suggest the best correction for an address."""
            if not address:
                return "", 0.0
            
            best_match = None
            best_score = 0.0
            
            for known_addr in known_addresses:
                score = calculate_address_similarity(address, known_addr)
                if score > best_score and score >= 0.7:  # Minimum threshold for suggestions
                    best_score = score
                    best_match = known_addr
            
            return best_match if best_match else "", best_score
        
        # Apply suggestions
        df_with_suggestions = df.with_columns([
            df[address_col].map_elements(lambda addr: suggest_correction(addr)[0], return_dtype=pl.String).alias("suggested_address"),
            df[address_col].map_elements(lambda addr: suggest_correction(addr)[1], return_dtype=pl.Float64).alias("suggestion_confidence")
        ])
        
        return df_with_suggestions
    
    def get_cluster_summary(self, df: pl.DataFrame, address_col: str = "Cleaned Address") -> Dict:
        """Get summary statistics about address clustering."""
        if 'address_cluster' not in df.columns:
            return {}
        
        cluster_counts = df['address_cluster'].value_counts().sort('count', descending=True)
        
        return {
            'total_clusters': len(cluster_counts),
            'largest_cluster_size': cluster_counts['count'].max() if len(cluster_counts) > 0 else 0,
            'average_cluster_size': cluster_counts['count'].mean() if len(cluster_counts) > 0 else 0,
            'clusters_with_multiple_addresses': len(cluster_counts.filter(pl.col('count') > 1)),
            'top_clusters': cluster_counts.head(10).to_dicts()
        }
