"""
GeoJSON Export for Illinois Jail Database
Exports the Illinois jail database as GeoJSON for use in other mapping tools.
"""

import polars as pl
import json
from pathlib import Path
from typing import Dict, List, Any

def export_to_geojson(data_dir: str = None) -> str:
    """
    Export Illinois jail database to GeoJSON format.
    
    Args:
        data_dir: Directory containing the database
        
    Returns:
        Path to the exported GeoJSON file
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data/illinois_jail_analysis"
    else:
        data_dir = Path(data_dir)
    
    db_path = data_dir / "unified_illinois_jails.parquet"
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return None
    
    # Load data
    df = pl.read_parquet(db_path)
    print(f"Loaded {len(df)} records from database")
    
    # Filter geocoded data
    geocoded_df = df.filter(pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null())
    print(f"Found {len(geocoded_df)} geocoded facilities")
    
    if len(geocoded_df) == 0:
        print("No geocoded data to export!")
        return None
    
    # Create GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Convert each record to GeoJSON feature
    for row in geocoded_df.iter_rows(named=True):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])]
            },
            "properties": {
                "name": row.get("name", "Unknown"),
                "official_name": row.get("official_name", ""),
                "address": row.get("address", ""),
                "city": row.get("city", ""),
                "county": row.get("county", ""),
                "facility_type": row.get("facility_type", "unknown"),
                "phone": row.get("phone", ""),
                "capacity": row.get("capacity", ""),
                "geocoded_confidence": float(row.get("geocoded_confidence", 0.0)),
                "geocoded_method": row.get("geocoded_method", ""),
                "geocoded_formatted_address": row.get("geocoded_formatted_address", ""),
                "county_seat": row.get("county_seat", ""),
                "data_source": row.get("data_source", ""),
                "status": row.get("status", "")
            }
        }
        geojson["features"].append(feature)
    
    # Export to file
    output_path = data_dir / "illinois_jails.geojson"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"GeoJSON exported to: {output_path}")
    print(f"Exported {len(geojson['features'])} features")
    
    # Also create a simplified version for easier use
    simple_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for row in geocoded_df.iter_rows(named=True):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])]
            },
            "properties": {
                "name": row.get("name", "Unknown"),
                "type": row.get("facility_type", "unknown"),
                "county": row.get("county", ""),
                "confidence": float(row.get("geocoded_confidence", 0.0))
            }
        }
        simple_geojson["features"].append(feature)
    
    simple_output_path = data_dir / "illinois_jails_simple.geojson"
    with open(simple_output_path, 'w', encoding='utf-8') as f:
        json.dump(simple_geojson, f, indent=2, ensure_ascii=False)
    
    print(f"Simple GeoJSON exported to: {simple_output_path}")
    
    return str(output_path)

def create_geojson_summary(data_dir: str = None) -> Dict[str, Any]:
    """
    Create a summary of the GeoJSON export.
    
    Returns:
        Dictionary with export statistics
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data/illinois_jail_analysis"
    else:
        data_dir = Path(data_dir)
    
    db_path = data_dir / "unified_illinois_jails.parquet"
    df = pl.read_parquet(db_path)
    
    geocoded_df = df.filter(pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null())
    
    # Count by facility type
    facility_counts = geocoded_df["facility_type"].value_counts()
    
    # Count by county
    county_counts = geocoded_df["county"].value_counts().sort("count", descending=True)
    
    summary = {
        "total_facilities": len(df),
        "geocoded_facilities": len(geocoded_df),
        "success_rate": len(geocoded_df) / len(df) * 100,
        "facility_types": facility_counts.to_dicts(),
        "top_counties": county_counts.head(10).to_dicts()
    }
    
    return summary

if __name__ == "__main__":
    print("Exporting Illinois Jail Database to GeoJSON")
    print("=" * 50)
    
    # Export GeoJSON
    geojson_path = export_to_geojson()
    
    if geojson_path:
        # Create summary
        summary = create_geojson_summary()
        
        print(f"\nExport Summary:")
        print(f"   Total Facilities: {summary['total_facilities']}")
        print(f"   Geocoded Facilities: {summary['geocoded_facilities']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        
        print(f"\nFacility Types:")
        for item in summary['facility_types']:
            print(f"   {item['facility_type']}: {item['count']}")
        
        print(f"\nTop Counties:")
        for item in summary['top_counties']:
            if item['county']:  # Skip empty counties
                print(f"   {item['county']}: {item['count']}")
        
        print(f"\nGeoJSON files created successfully!")
        print(f"Full GeoJSON: {geojson_path}")
        print(f"Simple GeoJSON: {Path(geojson_path).parent / 'illinois_jails_simple.geojson'}")
        print(f"\nYou can now use these GeoJSON files in:")
        print(f"   - QGIS")
        print(f"   - ArcGIS")
        print(f"   - Mapbox Studio")
        print(f"   - Any GeoJSON-compatible mapping tool")
    else:
        print("Export failed!")
