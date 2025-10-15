"""
Leaflet Interactive Map Creator for Illinois Jail Database
Creates interactive maps using Leaflet for the Illinois jail database.
"""

import polars as pl
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
import os

class IllinoisJailLeafletMap:
    """Creates interactive maps using Leaflet for Illinois jail data."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to the correct path relative to this file
            self.data_dir = Path(__file__).parent.parent / "data/illinois_jail_analysis"
        else:
            self.data_dir = Path(data_dir)
        
        # Color mapping for facility types
        self.facility_colors = {
            'county': '#FF6B6B',
            'municipal': '#4ECDC4', 
            'juvenile': '#45B7D1',
            'correctional': '#96CEB4',
            'unknown': '#95A5A6'
        }
        
        # Icon mapping for facility types
        self.facility_icons = {
            'county': 'home',
            'municipal': 'building',
            'juvenile': 'child',
            'correctional': 'lock',
            'unknown': 'question'
        }
    
    def create_interactive_map(self, 
                             map_type: str = "all",
                             output_file: str = "illinois_jails_leaflet.html") -> str:
        """
        Create an interactive map using Leaflet.
        
        Args:
            map_type: Type of map ('all', 'geocoded', 'county', 'municipal')
            output_file: Output HTML file name
            
        Returns:
            Path to the created HTML file
        """
        print(f"🗺️ Creating Leaflet interactive map: {map_type}")
        
        # Load data
        data = self._load_data(map_type)
        
        if data.empty:
            print("❌ No data to map!")
            return None
        
        # Create Leaflet HTML
        html_content = self._create_leaflet_html(data, map_type)
        
        # Save HTML file
        output_path = self.data_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Leaflet map created: {output_path}")
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
        
        # Convert to pandas for Leaflet
        pandas_df = df.to_pandas()
        
        print(f"📊 Loaded {len(pandas_df)} records for {map_type} map")
        return pandas_df
    
    def _create_leaflet_html(self, data: pd.DataFrame, map_type: str) -> str:
        """Create Leaflet HTML content."""
        
        # Filter geocoded data
        geocoded_data = data[data['latitude'].notna() & data['longitude'].notna()].copy()
        
        if geocoded_data.empty:
            print("❌ No geocoded data to map!")
            return self._create_empty_map_html(map_type)
        
        # Calculate center point
        center_lat = geocoded_data['latitude'].mean()
        center_lon = geocoded_data['longitude'].mean()
        
        # Prepare data for JavaScript
        markers_data = []
        for _, row in geocoded_data.iterrows():
            markers_data.append({
                'name': row.get('name', 'Unknown'),
                'address': row.get('address', ''),
                'city': row.get('city', ''),
                'county': row.get('county', ''),
                'facility_type': row.get('facility_type', 'unknown'),
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'confidence': float(row.get('geocoded_confidence', 0.0)),
                'phone': row.get('phone', ''),
                'capacity': row.get('capacity', ''),
                'data_source': row.get('data_source', 'unknown')
            })
        
        # Calculate statistics
        total_facilities = len(data)
        geocoded_count = len(geocoded_data)
        county_count = len(data[data['facility_type'] == 'county'])
        municipal_count = len(data[data['facility_type'] == 'municipal'])
        success_rate = (geocoded_count / total_facilities * 100) if total_facilities > 0 else 0
        
        # Create HTML template
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Illinois Jails Interactive Map - {map_type} (Leaflet)</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css" />
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f8f9fa;
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
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 1000;
            max-width: 350px;
            backdrop-filter: blur(10px);
        }}
        .info-panel h2 {{
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 24px;
            font-weight: 600;
        }}
        .info-panel p {{
            margin: 8px 0;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        .legend {{
            margin-top: 15px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
        }}
        .legend h4 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 16px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 8px 0;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .legend-text {{
            font-size: 14px;
            color: #34495e;
        }}
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #2c3e50;
            font-size: 18px;
            z-index: 2000;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">Loading Illinois Jails Map...</div>
    
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
        
        <div class="legend">
            <h4>Facility Types</h4>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #FF6B6B;"></div>
                <span class="legend-text">County Jails</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #4ECDC4;"></div>
                <span class="legend-text">Municipal Jails</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #45B7D1;"></div>
                <span class="legend-text">Juvenile Facilities</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #96CEB4;"></div>
                <span class="legend-text">Correctional</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #95A5A6;"></div>
                <span class="legend-text">Other</span>
            </div>
        </div>
        
        <p style="margin-top: 15px; font-size: 12px; color: #95A5A6;">
            <em>Interactive map powered by Leaflet</em>
        </p>
    </div>
    
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
    <script>
        // Hide loading screen
        document.getElementById('loading').style.display = 'none';
        
        // Initialize map
        const map = L.map('map').setView([{center_lat}, {center_lon}], 7);
        
        // Add tile layer
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }}).addTo(map);
        
        // Add additional tile layers
        const cartoDB = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }});
        
        const cartoDBDark = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }});
        
        // Create marker cluster group
        const markers = L.markerClusterGroup({{
            chunkedLoading: true,
            maxClusterRadius: 50
        }});
        
        // Facility type colors and icons
        const facilityColors = {facility_colors};
        const facilityIcons = {facility_icons};
        
        // Add markers
        const markersData = {markers_data};
        
        markersData.forEach(function(facility) {{
            const color = facilityColors[facility.facility_type] || '#95A5A6';
            
            // Create custom icon with colored circle
            const customIcon = L.divIcon({{
                className: 'custom-marker',
                html: `<div style="background-color: ${{color}}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }});
            
            // Create popup content
            const popupContent = `
                <div style="font-family: Arial, sans-serif; width: 250px;">
                    <h3 style="margin: 0 0 10px 0; color: #2c3e50;">${{facility.name}}</h3>
                    <p style="margin: 5px 0;"><strong>Type:</strong> ${{facility.facility_type.charAt(0).toUpperCase() + facility.facility_type.slice(1)}}</p>
                    <p style="margin: 5px 0;"><strong>Address:</strong> ${{facility.address}}</p>
                    <p style="margin: 5px 0;"><strong>City:</strong> ${{facility.city || 'N/A'}}</p>
                    <p style="margin: 5px 0;"><strong>County:</strong> ${{facility.county || 'N/A'}}</p>
                    ${{facility.phone ? `<p style="margin: 5px 0;"><strong>Phone:</strong> ${{facility.phone}}</p>` : ''}}
                    ${{facility.capacity ? `<p style="margin: 5px 0;"><strong>Capacity:</strong> ${{facility.capacity}}</p>` : ''}}
                    <p style="margin: 5px 0;"><strong>Confidence:</strong> ${{(facility.confidence * 100).toFixed(1)}}%</p>
                </div>
            `;
            
            // Create marker
            const marker = L.marker([facility.latitude, facility.longitude], {{
                icon: customIcon
            }}).bindPopup(popupContent);
            
            markers.addLayer(marker);
        }});
        
        // Add markers to map
        map.addLayer(markers);
        
        // Add layer control
        const baseMaps = {{
            "OpenStreetMap": L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }}),
            "CartoDB Light": cartoDB,
            "CartoDB Dark": cartoDBDark
        }};
        
        L.control.layers(baseMaps).addTo(map);
        
        // Fit map to show all markers
        if (markersData.length > 0) {{
            const group = new L.featureGroup(markers.getLayers());
            map.fitBounds(group.getBounds().pad(0.1));
        }}
        
        // Add click handler for debugging
        map.on('click', function(e) {{
            console.log('Map clicked at:', e.latlng);
        }});
    </script>
</body>
</html>
        """
        
        # Fill template
        html_content = html_template.format(
            map_type=map_type,
            total_facilities=total_facilities,
            geocoded_count=geocoded_count,
            county_count=county_count,
            municipal_count=municipal_count,
            success_rate=success_rate,
            center_lat=center_lat,
            center_lon=center_lon,
            facility_colors=json.dumps(self.facility_colors),
            facility_icons=json.dumps(self.facility_icons),
            markers_data=json.dumps(markers_data)
        )
        
        return html_content
    
    def _create_empty_map_html(self, map_type: str) -> str:
        """Create empty map HTML when no data is available."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Illinois Jails Interactive Map - {map_type} (Leaflet)</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ width: 100vw; height: 100vh; }}
        .no-data {{ 
            position: absolute; 
            top: 50%; 
            left: 50%; 
            transform: translate(-50%, -50%); 
            text-align: center; 
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="no-data">
        <h2>No Data Available</h2>
        <p>No geocoded facilities found for {map_type} map.</p>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([40.0, -89.0], 7);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(map);
    </script>
</body>
</html>
        """
    
    def create_multiple_maps(self) -> List[str]:
        """Create multiple map types."""
        map_types = ["all", "geocoded", "county", "municipal", "juvenile"]
        created_maps = []
        
        for map_type in map_types:
            output_file = f"illinois_jails_{map_type}_leaflet.html"
            map_path = self.create_interactive_map(map_type, output_file)
            if map_path:
                created_maps.append(map_path)
        
        return created_maps
    
    def open_map_in_browser(self, map_path: str):
        """Open map in default browser."""
        try:
            webbrowser.open(f"file://{os.path.abspath(map_path)}")
            print(f"🌐 Opened Leaflet map in browser: {map_path}")
        except Exception as e:
            print(f"❌ Could not open browser: {e}")
            print(f"📁 Open manually: {map_path}")

def create_illinois_jail_leaflet_maps():
    """Main function to create Illinois jail Leaflet maps."""
    print("🗺️ Creating Illinois Jail Interactive Maps with Leaflet")
    print("=" * 60)
    
    # Create map creator
    map_creator = IllinoisJailLeafletMap()
    
    # Create all map types
    created_maps = map_creator.create_multiple_maps()
    
    print(f"\n✅ Created {len(created_maps)} Leaflet interactive maps:")
    for map_path in created_maps:
        print(f"   📁 {map_path}")
    
    # Open the main map
    if created_maps:
        map_creator.open_map_in_browser(created_maps[0])
    
    return created_maps

if __name__ == "__main__":
    maps = create_illinois_jail_leaflet_maps()
    print("\n🎉 Leaflet interactive maps created successfully!")
    print("💡 Maps work without any API keys!")
