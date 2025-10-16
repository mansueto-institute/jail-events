"""
Interactive Dashboard Creator for Illinois Jail Data
Creates comprehensive dashboards with maps, charts, and analytics.
"""

import polars as pl
import pandas as pd
import folium
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime
import webbrowser

class IllinoisJailDashboard:
    """
    Creates interactive dashboards for Illinois jail data analysis.
    """
    
    def __init__(self, 
                 linked_data_path: str = None,
                 geocoded_db_path: str = None):
        # Set default paths if not provided
        if linked_data_path is None:
            linked_data_path = "data/illinois_jail_analysis/linked_jail_data.parquet"
        if geocoded_db_path is None:
            geocoded_db_path = "data/illinois_jail_analysis/unified_illinois_jails.parquet"
        
        self.linked_data_path = Path(linked_data_path)
        self.geocoded_db_path = Path(geocoded_db_path)
        self.linked_data_df: Optional[pl.DataFrame] = None
        self.geocoded_db_df: Optional[pl.DataFrame] = None
        self.output_dir = Path("data/illinois_jail_analysis/dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Load linked data and geocoded database."""
        print("📂 Loading data for dashboard...")
        
        # Load linked data
        if not self.linked_data_path.exists():
            raise FileNotFoundError(f"Linked data not found: {self.linked_data_path}")
        
        self.linked_data_df = pl.read_parquet(self.linked_data_path)
        print(f"   📊 Loaded {len(self.linked_data_df)} linked records")
        
        # Load geocoded database
        if not self.geocoded_db_path.exists():
            raise FileNotFoundError(f"Geocoded database not found: {self.geocoded_db_path}")
        
        self.geocoded_db_df = pl.read_parquet(self.geocoded_db_path)
        print(f"   📍 Loaded {len(self.geocoded_db_df)} geocoded facilities")
        
        return self.linked_data_df, self.geocoded_db_df
    
    def create_time_series_charts(self) -> List[str]:
        """Create time series visualization charts."""
        print("📈 Creating time series charts...")
        
        if self.linked_data_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Convert to pandas for easier plotting
        df_pandas = self.linked_data_df.to_pandas()
        
        # Clean dates
        df_pandas['cleaned_date'] = pd.to_datetime(df_pandas['Date'], errors='coerce')
        df_pandas = df_pandas.dropna(subset=['cleaned_date'])
        
        # Create time series data
        df_pandas['year'] = df_pandas['cleaned_date'].dt.year
        df_pandas['month'] = df_pandas['cleaned_date'].dt.month
        df_pandas['year_month'] = df_pandas['cleaned_date'].dt.to_period('M')
        
        chart_files = []
        
        # 1. Yearly trends
        yearly_counts = df_pandas.groupby('year').size().reset_index(name='count')
        fig_yearly = px.line(yearly_counts, x='year', y='count', 
                           title='Jail Incidents by Year',
                           labels={'count': 'Number of Incidents', 'year': 'Year'})
        fig_yearly.update_layout(height=400)
        
        yearly_file = self.output_dir / "yearly_trends.html"
        pyo.plot(fig_yearly, filename=str(yearly_file), auto_open=False)
        chart_files.append(str(yearly_file))
        
        # 2. Monthly patterns
        monthly_counts = df_pandas.groupby('month').size().reset_index(name='count')
        fig_monthly = px.bar(monthly_counts, x='month', y='count',
                           title='Jail Incidents by Month',
                           labels={'count': 'Number of Incidents', 'month': 'Month'})
        fig_monthly.update_layout(height=400)
        
        monthly_file = self.output_dir / "monthly_patterns.html"
        pyo.plot(fig_monthly, filename=str(monthly_file), auto_open=False)
        chart_files.append(str(monthly_file))
        
        # 3. Facility type distribution
        facility_counts = df_pandas['matched_facility_type'].value_counts().head(10)
        fig_facility = px.pie(values=facility_counts.values, names=facility_counts.index,
                            title='Distribution by Facility Type (Top 10)')
        fig_facility.update_layout(height=400)
        
        facility_file = self.output_dir / "facility_distribution.html"
        pyo.plot(fig_facility, filename=str(facility_file), auto_open=False)
        chart_files.append(str(facility_file))
        
        # 4. County distribution
        county_counts = df_pandas['matched_county'].value_counts().head(10)
        county_df = pd.DataFrame({
            'County': county_counts.index,
            'Count': county_counts.values
        })
        fig_county = px.bar(county_df, x='County', y='Count',
                          title='Jail Incidents by County (Top 10)',
                          labels={'Count': 'Number of Incidents'})
        fig_county.update_layout(height=400, xaxis_tickangle=-45)
        
        county_file = self.output_dir / "county_distribution.html"
        pyo.plot(fig_county, filename=str(county_file), auto_open=False)
        chart_files.append(str(county_file))
        
        # 5. Occurrence types
        occurrence_counts = df_pandas['Occurrence'].value_counts().head(15)
        occurrence_df = pd.DataFrame({
            'Occurrence': occurrence_counts.index,
            'Count': occurrence_counts.values
        })
        fig_occurrence = px.bar(occurrence_df, x='Occurrence', y='Count',
                              title='Most Common Occurrence Types (Top 15)',
                              labels={'Count': 'Number of Incidents'})
        fig_occurrence.update_layout(height=500, xaxis_tickangle=-45)
        
        occurrence_file = self.output_dir / "occurrence_types.html"
        pyo.plot(fig_occurrence, filename=str(occurrence_file), auto_open=False)
        chart_files.append(str(occurrence_file))
        
        print(f"   ✅ Created {len(chart_files)} time series charts")
        return chart_files
    
    def create_interactive_map(self) -> str:
        """Create an interactive map showing jail facilities and incidents."""
        print("🗺️ Creating interactive map...")
        
        if self.linked_data_df is None or self.geocoded_db_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Get matched records with coordinates
        matched_records = self.linked_data_df.filter(
            (pl.col("matched_latitude").is_not_null()) & 
            (pl.col("matched_longitude").is_not_null())
        )
        
        if len(matched_records) == 0:
            print("   ⚠️ No matched records with coordinates found")
            return ""
        
        # Convert to pandas for easier processing
        matched_pandas = matched_records.to_pandas()
        
        # Create base map centered on Illinois
        m = folium.Map(
            location=[40.0, -89.0],  # Center of Illinois
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # Add facility markers
        facilities = self.geocoded_db_df.filter(pl.col("latitude").is_not_null())
        facilities_pandas = facilities.to_pandas()
        
        # Color code by facility type
        facility_colors = {
            'county': 'blue',
            'municipal': 'green',
            'juvenile': 'orange',
            'state': 'red',
            'federal': 'purple'
        }
        
        for _, facility in facilities_pandas.iterrows():
            color = facility_colors.get(facility.get('facility_type', 'unknown'), 'gray')
            
            folium.CircleMarker(
                location=[facility['latitude'], facility['longitude']],
                radius=8,
                popup=f"""
                <b>{facility['name']}</b><br>
                Type: {facility.get('facility_type', 'Unknown')}<br>
                County: {facility.get('county', 'Unknown')}<br>
                Address: {facility.get('address', 'Unknown')}
                """,
                color='black',
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
        
        # Add incident clusters
        from folium.plugins import MarkerCluster
        
        incident_cluster = MarkerCluster(name='Jail Incidents')
        
        for _, incident in matched_pandas.iterrows():
            folium.CircleMarker(
                location=[incident['matched_latitude'], incident['matched_longitude']],
                radius=3,
                popup=f"""
                <b>Incident Report</b><br>
                Facility: {incident.get('matched_facility_name', 'Unknown')}<br>
                Date: {incident.get('Date', 'Unknown')}<br>
                Occurrence: {incident.get('Occurrence', 'Unknown')}<br>
                Injuries: {incident.get('Injuries?', 'Unknown')}<br>
                Death: {incident.get('Resulting Death?', 'Unknown')}<br>
                Match Confidence: {incident.get('match_confidence', 0):.2f}
                """,
                color='red',
                fillColor='red',
                fillOpacity=0.6
            ).add_to(incident_cluster)
        
        incident_cluster.add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Facility Types</b></p>
        <p><i class="fa fa-circle" style="color:blue"></i> County</p>
        <p><i class="fa fa-circle" style="color:green"></i> Municipal</p>
        <p><i class="fa fa-circle" style="color:orange"></i> Juvenile</p>
        <p><i class="fa fa-circle" style="color:red"></i> State</p>
        <p><i class="fa fa-circle" style="color:purple"></i> Federal</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save map
        map_file = self.output_dir / "illinois_jail_map.html"
        m.save(str(map_file))
        
        print(f"   ✅ Interactive map created: {map_file}")
        return str(map_file)
    
    def create_summary_dashboard(self) -> str:
        """Create a comprehensive summary dashboard."""
        print("📊 Creating summary dashboard...")
        
        if self.linked_data_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Calculate summary statistics
        total_records = len(self.linked_data_df)
        matched_records = len(self.linked_data_df.filter(pl.col("match_confidence") > 0))
        match_rate = matched_records / total_records * 100
        
        # Top facilities by incident count
        top_facilities = (self.linked_data_df
                         .filter(pl.col("match_confidence") > 0)
                         .group_by("matched_facility_name")
                         .len()
                         .sort("len", descending=True)
                         .head(10))
        
        # Top counties by incident count
        top_counties = (self.linked_data_df
                       .filter(pl.col("match_confidence") > 0)
                       .group_by("matched_county")
                       .len()
                       .sort("len", descending=True)
                       .head(10))
        
        # Occurrence type distribution
        occurrence_dist = (self.linked_data_df
                          .group_by("Occurrence")
                          .len()
                          .sort("len", descending=True)
                          .head(15))
        
        # Injury and death statistics
        injury_stats = self.linked_data_df.group_by("Injuries?").len()
        death_stats = self.linked_data_df.group_by("Resulting Death?").len()
        
        # Create HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Illinois Jail Data Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background-color: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #e74c3c; }}
                .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .chart-container {{ margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Illinois Jail Data Dashboard</h1>
                    <p>Comprehensive Analysis of Jail Incidents and Facilities</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_records:,}</div>
                        <div class="stat-label">Total Records</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{matched_records:,}</div>
                        <div class="stat-label">Matched Records</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{match_rate:.1f}%</div>
                        <div class="stat-label">Match Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{self.linked_data_df['matched_facility_name'].n_unique()}</div>
                        <div class="stat-label">Unique Facilities</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📈 Top Facilities by Incident Count</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Facility Name</th>
                                <th>Incident Count</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, row in enumerate(top_facilities.iter_rows(named=True), 1):
            facility_name = row.get('matched_facility_name', 'Unknown')
            count = row.get('len', 0)
            html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{facility_name}</td>
                                <td>{count:,}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>🏘️ Top Counties by Incident Count</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>County</th>
                                <th>Incident Count</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, row in enumerate(top_counties.iter_rows(named=True), 1):
            county_name = row.get('matched_county', 'Unknown')
            count = row.get('len', 0)
            html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{county_name}</td>
                                <td>{count:,}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>📋 Most Common Occurrence Types</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Occurrence Type</th>
                                <th>Count</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, row in enumerate(occurrence_dist.iter_rows(named=True), 1):
            occurrence = row.get('Occurrence', 'Unknown')
            count = row.get('len', 0)
            html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{occurrence}</td>
                                <td>{count:,}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>⚠️ Injury and Death Statistics</h2>
                    <div class="stats-grid">
        """
        
        for row in injury_stats.iter_rows(named=True):
            injury_status = row.get('Injuries?', 'Unknown')
            count = row.get('len', 0)
            percentage = count / total_records * 100
            html_content += f"""
                        <div class="stat-card">
                            <div class="stat-number">{count:,}</div>
                            <div class="stat-label">Injuries: {injury_status} ({percentage:.1f}%)</div>
                        </div>
            """
        
        for row in death_stats.iter_rows(named=True):
            death_status = row.get('Resulting Death?', 'Unknown')
            count = row.get('len', 0)
            percentage = count / total_records * 100
            html_content += f"""
                        <div class="stat-card">
                            <div class="stat-number">{count:,}</div>
                            <div class="stat-label">Deaths: {death_status} ({percentage:.1f}%)</div>
                        </div>
            """
        
        html_content += f"""
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Data Source: Illinois Jail Reports Database</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save dashboard
        dashboard_file = self.output_dir / "summary_dashboard.html"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"   ✅ Summary dashboard created: {dashboard_file}")
        return str(dashboard_file)
    
    def create_comprehensive_dashboard(self) -> Dict[str, str]:
        """Create all dashboard components."""
        print("🚀 Creating Comprehensive Illinois Jail Dashboard")
        print("=" * 55)
        
        # Load data
        linked_data, geocoded_db = self.load_data()
        
        # Create all components
        dashboard_files = {}
        
        # 1. Time series charts
        chart_files = self.create_time_series_charts()
        dashboard_files['charts'] = chart_files
        
        # 2. Interactive map
        map_file = self.create_interactive_map()
        if map_file:
            dashboard_files['map'] = map_file
        
        # 3. Summary dashboard
        summary_file = self.create_summary_dashboard()
        dashboard_files['summary'] = summary_file
        
        # 4. Create index page
        index_file = self.create_dashboard_index(dashboard_files)
        dashboard_files['index'] = index_file
        
        print(f"\n🎉 Dashboard created successfully!")
        print(f"   📁 Output directory: {self.output_dir}")
        print(f"   📊 Components created: {len(dashboard_files)}")
        
        return dashboard_files
    
    def create_dashboard_index(self, dashboard_files: Dict[str, Any]) -> str:
        """Create an index page linking all dashboard components."""
        print("📑 Creating dashboard index page...")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Illinois Jail Data Dashboard - Index</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; color: #2c3e50; margin-bottom: 40px; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .link-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .link-card {{ background-color: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; transition: transform 0.2s; }}
                .link-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .link-card a {{ text-decoration: none; color: #2c3e50; }}
                .link-card h3 {{ margin-top: 0; color: #e74c3c; }}
                .link-card p {{ color: #7f8c8d; }}
                .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Illinois Jail Data Dashboard</h1>
                    <p>Comprehensive Analysis and Visualization of Jail Incidents</p>
                </div>
                
                <div class="section">
                    <h2>📊 Main Dashboard</h2>
                    <div class="link-grid">
                        <div class="link-card">
                            <a href="summary_dashboard.html">
                                <h3>📈 Summary Dashboard</h3>
                                <p>Overview statistics, top facilities, counties, and occurrence types</p>
                            </a>
                        </div>
                        <div class="link-card">
                            <a href="illinois_jail_map.html">
                                <h3>🗺️ Interactive Map</h3>
                                <p>Geographic visualization of facilities and incidents</p>
                            </a>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📈 Time Series Analysis</h2>
                    <div class="link-grid">
        """
        
        chart_names = {
            'yearly_trends.html': '📅 Yearly Trends',
            'monthly_patterns.html': '📆 Monthly Patterns',
            'facility_distribution.html': '🏛️ Facility Distribution',
            'county_distribution.html': '🏘️ County Distribution',
            'occurrence_types.html': '📋 Occurrence Types'
        }
        
        for chart_file in dashboard_files.get('charts', []):
            chart_name = Path(chart_file).name
            display_name = chart_names.get(chart_name, chart_name)
            html_content += f"""
                        <div class="link-card">
                            <a href="{chart_name}">
                                <h3>{display_name}</h3>
                                <p>Interactive charts and visualizations</p>
                            </a>
                        </div>
            """
        
        html_content += f"""
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Data Source: Illinois Jail Reports Database</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        index_file = self.output_dir / "index.html"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"   ✅ Index page created: {index_file}")
        return str(index_file)

def create_illinois_jail_dashboard():
    """Main function to create the Illinois jail dashboard."""
    print("🚀 Illinois Jail Dashboard Creator")
    print("=" * 40)
    
    # Initialize dashboard creator
    dashboard = IllinoisJailDashboard()
    
    # Create comprehensive dashboard
    dashboard_files = dashboard.create_comprehensive_dashboard()
    
    print(f"\n🎉 Dashboard creation completed!")
    print(f"   📁 All files saved to: {dashboard.output_dir}")
    print(f"   🌐 Open index.html in your browser to view the dashboard")
    
    return dashboard, dashboard_files

if __name__ == "__main__":
    dashboard, files = create_illinois_jail_dashboard()
    print("\n🎉 Dashboard creation completed successfully!")
