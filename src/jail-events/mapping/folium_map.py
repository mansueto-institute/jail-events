"""
Folium Interactive Map Creator for Illinois Jail Database
Creates interactive maps using Folium for the Illinois jail database.
"""

import polars as pl
import pandas as pd
import folium
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
import os

class IllinoisJailFoliumMap:
    """Creates interactive maps using Folium for Illinois jail data."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to the correct path relative to this file
            self.data_dir = Path(__file__).parent.parent / "data/illinois_jail_analysis"
        else:
            self.data_dir = Path(data_dir)
        
        # Color mapping for facility types
        self.facility_colors = {
            'county': 'red',
            'municipal': 'blue', 
            'juvenile': 'green',
            'correctional': 'purple',
            'unknown': 'gray'
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
                             output_file: str = "illinois_jails_map.html") -> str:
        """
        Create an interactive map using Folium.
        
        Args:
            map_type: Type of map ('all', 'geocoded', 'county', 'municipal')
            output_file: Output HTML file name
            
        Returns:
            Path to the created HTML file
        """
        print(f"🗺️ Creating interactive map: {map_type}")
        
        # Load data
        data = self._load_data(map_type)
        
        if data.empty:
            print("❌ No data to map!")
            return None
        
        # Create map
        map_obj = self._create_folium_map(data, map_type)
        
        # Save map
        output_path = self.data_dir / output_file
        map_obj.save(str(output_path))
        
        print(f"✅ Interactive map created: {output_path}")
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
        
        # Convert to pandas for Folium
        pandas_df = df.to_pandas()
        
        print(f"📊 Loaded {len(pandas_df)} records for {map_type} map")
        return pandas_df
    
    def _create_folium_map(self, data: pd.DataFrame, map_type: str) -> folium.Map:
        """Create Folium map with data."""
        
        # Filter geocoded data
        geocoded_data = data[data['latitude'].notna() & data['longitude'].notna()].copy()
        
        if geocoded_data.empty:
            print("❌ No geocoded data to map!")
            return folium.Map(location=[40.0, -89.0], zoom_start=6)
        
        # Calculate center point
        center_lat = geocoded_data['latitude'].mean()
        center_lon = geocoded_data['longitude'].mean()
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # Add different tile layers with proper attribution
        folium.TileLayer(
            'CartoDB Positron', 
            name='Light Mode',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        ).add_to(m)
        
        folium.TileLayer(
            'CartoDB Dark_Matter', 
            name='Dark Mode',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        ).add_to(m)
        
        folium.TileLayer(
            'Stamen Terrain', 
            name='Terrain',
            attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        ).add_to(m)
        
        # Create feature groups for different facility types
        facility_groups = {}
        for facility_type in geocoded_data['facility_type'].unique():
            if pd.notna(facility_type):
                facility_groups[facility_type] = folium.FeatureGroup(
                    name=f"{facility_type.title()} Jails"
                )
                m.add_child(facility_groups[facility_type])
        
        # Add markers for each facility
        for _, row in geocoded_data.iterrows():
            if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                continue
            
            facility_type = row.get('facility_type', 'unknown')
            color = self.facility_colors.get(facility_type, 'gray')
            icon = self.facility_icons.get(facility_type, 'question')
            
            # Create popup content
            popup_content = self._create_popup_content(row)
            
            # Create marker
            marker = folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=row.get('name', 'Unknown Facility'),
                icon=folium.Icon(
                    color=color,
                    icon=icon,
                    prefix='fa'
                )
            )
            
            # Add to appropriate group
            if facility_type in facility_groups:
                marker.add_to(facility_groups[facility_type])
            else:
                marker.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add legend
        self._add_legend(m)
        
        # Add statistics
        self._add_statistics(m, geocoded_data, map_type)
        
        return m
    
    def _create_popup_content(self, row: pd.Series) -> str:
        """Create popup content for marker."""
        content = f"""
        <div style="font-family: Arial, sans-serif; width: 250px;">
            <h3 style="margin: 0 0 10px 0; color: #333;">{row.get('name', 'Unknown Facility')}</h3>
            <p style="margin: 5px 0;"><strong>Type:</strong> {row.get('facility_type', 'Unknown').title()}</p>
            <p style="margin: 5px 0;"><strong>Address:</strong> {row.get('address', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>City:</strong> {row.get('city', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>County:</strong> {row.get('county', 'N/A')}</p>
        """
        
        if pd.notna(row.get('phone')):
            content += f'<p style="margin: 5px 0;"><strong>Phone:</strong> {row["phone"]}</p>'
        
        if pd.notna(row.get('capacity')):
            content += f'<p style="margin: 5px 0;"><strong>Capacity:</strong> {row["capacity"]}</p>'
        
        if pd.notna(row.get('geocoded_confidence')):
            confidence = float(row['geocoded_confidence'])
            content += f'<p style="margin: 5px 0;"><strong>Confidence:</strong> {confidence:.2f}</p>'
        
        content += "</div>"
        return content
    
    def _add_legend(self, map_obj: folium.Map):
        """Add legend to map."""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Facility Types</b></p>
        <p><i class="fa fa-home" style="color:red"></i> County Jails</p>
        <p><i class="fa fa-building" style="color:blue"></i> Municipal Jails</p>
        <p><i class="fa fa-child" style="color:green"></i> Juvenile Facilities</p>
        <p><i class="fa fa-lock" style="color:purple"></i> Correctional Facilities</p>
        <p><i class="fa fa-question" style="color:gray"></i> Other</p>
        </div>
        '''
        map_obj.get_root().html.add_child(folium.Element(legend_html))
    
    def _add_statistics(self, map_obj: folium.Map, data: pd.DataFrame, map_type: str):
        """Add statistics panel to map."""
        total_facilities = len(data)
        geocoded_count = len(data[data['latitude'].notna()])
        
        # Count by facility type
        facility_counts = data['facility_type'].value_counts()
        
        stats_html = f'''
        <div style="position: fixed; 
                    top: 50px; right: 50px; width: 250px; height: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px; border-radius: 5px;">
        <h4 style="margin: 0 0 10px 0;">Illinois Jails - {map_type.title()}</h4>
        <p style="margin: 5px 0;"><strong>Total Facilities:</strong> {total_facilities}</p>
        <p style="margin: 5px 0;"><strong>Geocoded:</strong> {geocoded_count}</p>
        <p style="margin: 5px 0;"><strong>Success Rate:</strong> {(geocoded_count/total_facilities*100):.1f}%</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0;"><strong>By Type:</strong></p>
        '''
        
        for facility_type, count in facility_counts.items():
            if pd.notna(facility_type):
                stats_html += f'<p style="margin: 2px 0;">{facility_type.title()}: {count}</p>'
        
        stats_html += '</div>'
        map_obj.get_root().html.add_child(folium.Element(stats_html))
    
    def create_multiple_maps(self) -> List[str]:
        """Create only the main comprehensive map."""
        created_maps = []
        
        # Only create the main "all" map
        output_file = "illinois_jails_all_map.html"
        map_path = self.create_interactive_map("all", output_file)
        if map_path:
            created_maps.append(map_path)
        
        return created_maps
    
    def open_map_in_browser(self, map_path: str):
        """Open map in default browser."""
        try:
            webbrowser.open(f"file://{os.path.abspath(map_path)}")
            print(f"🌐 Opened map in browser: {map_path}")
        except Exception as e:
            print(f"❌ Could not open browser: {e}")
            print(f"📁 Open manually: {map_path}")

def create_illinois_jail_maps():
    """Main function to create Illinois jail maps."""
    print("🗺️ Creating Illinois Jail Interactive Maps with Folium")
    print("=" * 60)
    
    # Create map creator
    map_creator = IllinoisJailFoliumMap()
    
    # Create all map types
    created_maps = map_creator.create_multiple_maps()
    
    print(f"\n✅ Created {len(created_maps)} interactive maps:")
    for map_path in created_maps:
        print(f"   📁 {map_path}")
    
    # Open the main map
    if created_maps:
        map_creator.open_map_in_browser(created_maps[0])
    
    return created_maps

if __name__ == "__main__":
    maps = create_illinois_jail_maps()
    print("\n🎉 Interactive maps created successfully!")
    print("💡 Maps are ready to use - no API keys required!")
