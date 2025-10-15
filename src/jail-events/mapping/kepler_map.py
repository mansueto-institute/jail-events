"""
Kepler.gl Interactive Map Creator for Illinois Jail Database
Creates interactive maps using Kepler.gl for the Illinois jail database.
"""

import polars as pl
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
import os

class IllinoisJailKeplerMap:
    """Creates interactive maps using Kepler.gl for Illinois jail data."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to the correct path relative to this file
            self.data_dir = Path(__file__).parent.parent / "data/illinois_jail_analysis"
        else:
            self.data_dir = Path(data_dir)
        self.kepler_config = self._get_default_kepler_config()
    
    def create_interactive_map(self, 
                             map_type: str = "all",
                             output_file: str = "illinois_jails_kepler.html") -> str:
        """
        Create an interactive map using Kepler.gl.
        
        Args:
            map_type: Type of map ('all', 'geocoded', 'county', 'municipal')
            output_file: Output HTML file name
            
        Returns:
            Path to the created HTML file
        """
        print(f"🗺️ Creating Kepler.gl interactive map: {map_type}")
        
        # Load data
        data = self._load_data(map_type)
        
        if data.empty:
            print("❌ No data to map!")
            return None
        
        # Create Kepler.gl HTML
        html_content = self._create_kepler_html(data, map_type)
        
        # Save HTML file
        output_path = self.data_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Kepler.gl map created: {output_path}")
        return str(output_path)
    
    def _load_data(self, map_type: str) -> pd.DataFrame:
        """Load data based on map type."""
        db_path = self.data_dir / "unified_illinois_jails.parquet"
        
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return pd.DataFrame()
        
        # Load data
        df = pl.read_parquet(db_path)
        
        # Filter based on map type
        if map_type == "geocoded":
            df = df.filter(pl.col("latitude").is_not_null())
        elif map_type == "county":
            df = df.filter(pl.col("facility_type") == "county")
        elif map_type == "municipal":
            df = df.filter(pl.col("facility_type") == "municipal")
        elif map_type == "juvenile":
            df = df.filter(pl.col("facility_type") == "juvenile")
        
        # Convert to pandas for Kepler.gl
        pandas_df = df.to_pandas()
        
        print(f"📊 Loaded {len(pandas_df)} records for {map_type} map")
        return pandas_df
    
    def _create_kepler_html(self, data: pd.DataFrame, map_type: str) -> str:
        """Create Kepler.gl HTML content."""
        
        # Prepare data for Kepler.gl
        kepler_data = self._prepare_kepler_data(data)
        
        # Create HTML template
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Illinois Jails Interactive Map - {map_type} (Kepler.gl)</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: #1a1a1a;
        }}
        #map {{
            width: 100vw;
            height: 100vh;
        }}
        .info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 350px;
            backdrop-filter: blur(10px);
        }}
        .info-panel h2 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 24px;
        }}
        .info-panel p {{
            margin: 8px 0;
            color: #666;
            font-size: 14px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            font-size: 12px;
            color: #7f8c8d;
        }}
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 18px;
            z-index: 2000;
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">Loading Kepler.gl Map...</div>
    
    <div class="info-panel">
        <h2>Illinois Jails Map</h2>
        <p><strong>Type:</strong> {map_type}</p>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{total_facilities}</div>
                <div class="stat-label">Total Facilities</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{geocoded_count}</div>
                <div class="stat-label">Geocoded</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{county_count}</div>
                <div class="stat-label">County Jails</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{municipal_count}</div>
                <div class="stat-label">Municipal</div>
            </div>
        </div>
        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
        <p><em>Interactive map powered by Kepler.gl</em></p>
    </div>
    
    <div id="map"></div>
    
    <script src="https://unpkg.com/kepler.gl@3.0.0/dist/umd/kepler.gl.min.js"></script>
    <script>
        // Hide loading screen
        document.getElementById('loading').style.display = 'none';
        
        // Initialize Kepler.gl with OpenStreetMap (no API key required)
        const keplerGl = new KeplerGl.Map({{
            id: 'map',
            width: '100%',
            height: '100%',
            mapboxApiAccessToken: null, // No API key needed for OpenStreetMap
        }});
        
        // Data
        const data = {kepler_data};
        
        // Configuration
        const config = {kepler_config};
        
        // Add data to map
        keplerGl.addDataToMap({{
            datasets: data,
            config: config
        }});
        
        // Auto-fit to data
        setTimeout(() => {{
            keplerGl.fitBounds();
        }}, 2000);
        
        // Add click handler for markers
        keplerGl.on('click', (info) => {{
            if (info.object) {{
                console.log('Clicked facility:', info.object);
            }}
        }});
    </script>
</body>
</html>
        """
        
        # Calculate statistics
        total_facilities = len(data)
        geocoded_count = len(data[data['latitude'].notna()])
        county_count = len(data[data['facility_type'] == 'county'])
        municipal_count = len(data[data['facility_type'] == 'municipal'])
        success_rate = (geocoded_count / total_facilities * 100) if total_facilities > 0 else 0
        
        # Format data for Kepler.gl
        kepler_data_json = json.dumps(kepler_data, indent=2)
        kepler_config_json = json.dumps(self.kepler_config, indent=2)
        
        # Fill template
        html_content = html_template.format(
            map_type=map_type,
            total_facilities=total_facilities,
            geocoded_count=geocoded_count,
            county_count=county_count,
            municipal_count=municipal_count,
            success_rate=success_rate,
            kepler_data=kepler_data_json,
            kepler_config=kepler_config_json
        )
        
        return html_content
    
    def _prepare_kepler_data(self, data: pd.DataFrame) -> Dict:
        """Prepare data for Kepler.gl format."""
        
        # Filter out records without coordinates
        geocoded_data = data[data['latitude'].notna() & data['longitude'].notna()].copy()
        
        if geocoded_data.empty:
            return {
                "info": {
                    "id": "illinois_jails",
                    "label": "Illinois Jails",
                    "color": [255, 107, 107]
                },
                "data": []
            }
        
        # Prepare data for Kepler.gl
        kepler_data = []
        
        for _, row in geocoded_data.iterrows():
            kepler_data.append({
                "name": row.get('name', 'Unknown'),
                "address": row.get('address', ''),
                "city": row.get('city', ''),
                "county": row.get('county', ''),
                "facility_type": row.get('facility_type', 'unknown'),
                "latitude": float(row['latitude']),
                "longitude": float(row['longitude']),
                "confidence": float(row.get('geocoded_confidence', 0.0)),
                "phone": row.get('phone', ''),
                "capacity": row.get('capacity', ''),
                "data_source": row.get('data_source', 'unknown')
            })
        
        return {
            "info": {
                "id": "illinois_jails",
                "label": "Illinois Jails",
                "color": [255, 107, 107]
            },
            "data": kepler_data
        }
    
    def _get_default_kepler_config(self) -> Dict:
        """Get default Kepler.gl configuration."""
        return {
            "version": "v1",
            "config": {
                "visState": {
                    "filters": [],
                    "layers": [
                        {
                            "id": "illinois_jails_layer",
                            "type": "point",
                            "config": {
                                "dataId": "illinois_jails",
                                "label": "Illinois Jails",
                                "color": [255, 107, 107],
                                "columns": {
                                    "lat": "latitude",
                                    "lng": "longitude"
                                },
                                "isVisible": True,
                                "visConfig": {
                                    "opacity": 0.8,
                                    "strokeOpacity": 0.8,
                                    "thickness": 2,
                                    "strokeColor": [255, 255, 255],
                                    "colorRange": {
                                        "name": "Global Warming",
                                        "type": "sequential",
                                        "category": "Uber",
                                        "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"]
                                    },
                                    "radiusRange": [3, 15],
                                    "radius": 8,
                                    "filled": True,
                                    "enable3d": False,
                                    "sizeRange": [0, 10],
                                    "sizeScale": 1,
                                    "strokeWidthRange": [0, 10],
                                    "strokeWidthScale": 1,
                                    "heightRange": [0, 500],
                                    "heightScale": 1,
                                    "elevationScale": 1,
                                    "enableElevationZoomFactor": True,
                                    "stroked": True,
                                    "wireframe": False
                                },
                                "textLabel": [
                                    {
                                        "field": {
                                            "name": "name",
                                            "type": "string"
                                        },
                                        "color": [255, 255, 255],
                                        "size": 12,
                                        "offset": [0, 0],
                                        "anchor": "start",
                                        "alignment": "center"
                                    }
                                ]
                            },
                            "visualChannels": {
                                "colorField": {
                                    "name": "facility_type",
                                    "type": "string"
                                },
                                "colorScale": "ordinal",
                                "sizeField": {
                                    "name": "confidence",
                                    "type": "real"
                                },
                                "sizeScale": "linear"
                            }
                        }
                    ],
                    "interactionConfig": {
                        "tooltip": {
                            "fieldsToShow": {
                                "illinois_jails": [
                                    "name",
                                    "address",
                                    "city",
                                    "county",
                                    "facility_type",
                                    "confidence",
                                    "phone"
                                ]
                            },
                            "compareMode": False,
                            "compareType": "absolute",
                            "enabled": True
                        },
                        "brush": {
                            "size": 0.5,
                            "enabled": False
                        },
                        "geocoder": {
                            "enabled": False
                        },
                        "coordinate": {
                            "enabled": False
                        }
                    },
                    "layerBlending": "normal",
                    "splitMaps": [],
                    "animationConfig": {
                        "currentTime": None,
                        "speed": 1
                    }
                },
                "mapState": {
                    "bearing": 0,
                    "dragRotate": True,
                    "latitude": 40.0,
                    "longitude": -89.0,
                    "pitch": 0,
                    "zoom": 6,
                    "isSplit": False
                },
                "mapStyle": {
                    "styleType": "dark",
                    "topLayerGroups": {},
                    "visibleLayerGroups": {
                        "label": True,
                        "road": True,
                        "border": False,
                        "building": True,
                        "water": True,
                        "land": True,
                        "3d building": False
                    },
                    "threeDBuildingColor": [9.665468314712013, 17.18331578055358, 31.1442867897876],
                    "mapStyles": {}
                }
            }
        }
    
    def create_multiple_maps(self) -> List[str]:
        """Create multiple map types."""
        map_types = ["all", "geocoded", "county", "municipal", "juvenile"]
        created_maps = []
        
        for map_type in map_types:
            output_file = f"illinois_jails_{map_type}_kepler.html"
            map_path = self.create_interactive_map(map_type, output_file)
            if map_path:
                created_maps.append(map_path)
        
        return created_maps
    
    def open_map_in_browser(self, map_path: str):
        """Open map in default browser."""
        try:
            webbrowser.open(f"file://{os.path.abspath(map_path)}")
            print(f"🌐 Opened Kepler.gl map in browser: {map_path}")
        except Exception as e:
            print(f"❌ Could not open browser: {e}")
            print(f"📁 Open manually: {map_path}")

def create_illinois_jail_kepler_maps():
    """Main function to create Illinois jail Kepler.gl maps."""
    print("🗺️ Creating Illinois Jail Interactive Maps with Kepler.gl")
    print("=" * 60)
    
    # Create map creator
    map_creator = IllinoisJailKeplerMap()
    
    # Create all map types
    created_maps = map_creator.create_multiple_maps()
    
    print(f"\n✅ Created {len(created_maps)} Kepler.gl interactive maps:")
    for map_path in created_maps:
        print(f"   📁 {map_path}")
    
    # Open the main map
    if created_maps:
        map_creator.open_map_in_browser(created_maps[0])
    
    return created_maps

if __name__ == "__main__":
    maps = create_illinois_jail_kepler_maps()
    print("\n🎉 Kepler.gl interactive maps created successfully!")
    print("💡 Note: You'll need a Mapbox API token for full functionality.")