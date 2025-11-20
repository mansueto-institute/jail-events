"""
Interactive Dashboard Creator for Illinois Jail Data using Vega-Altair
Creates comprehensive dashboards with maps, charts, and analytics matching the presentation style.
"""

import polars as pl
import pandas as pd
import altair as alt
import folium
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import webbrowser

# Enable vegafusion for better performance
alt.data_transformers.enable("vegafusion")

class IllinoisJailAltairDashboard:
    """
    Creates interactive dashboards for Illinois jail data analysis using Vega-Altair.
    Matches the style and analysis from the Quarto presentation.
    """
    
    def __init__(self, 
                 cleaned_data_path: str = None,
                 geocoded_db_path: str = None):
        # Set default paths if not provided
        if cleaned_data_path is None:
            cleaned_data_path = "data/jails-data/output/jails_pdfs_cleaned.parquet"
        if geocoded_db_path is None:
            geocoded_db_path = "data/illinois_jail_analysis/unified_illinois_jails.parquet"
        
        self.cleaned_data_path = Path(cleaned_data_path)
        self.geocoded_db_path = Path(geocoded_db_path)
        self.cleaned_data_df: Optional[pl.DataFrame] = None
        self.geocoded_db_df: Optional[pl.DataFrame] = None
        self.output_dir = Path("data/illinois_jail_analysis/altair_dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Load cleaned data and geocoded database."""
        print("Loading data for Altair dashboard...")
        
        # Load cleaned data
        if not self.cleaned_data_path.exists():
            raise FileNotFoundError(f"Cleaned data not found: {self.cleaned_data_path}")
        
        self.cleaned_data_df = pl.read_parquet(self.cleaned_data_path)
        print(f"   Loaded {len(self.cleaned_data_df)} cleaned records")
        
        # Apply the same facility name cleaning as in the presentation
        self.cleaned_data_df = self.cleaned_data_df.with_columns(
            pl.when(pl.col("Cleaned Facility Name").str.contains("Peoria"))
            .then(pl.lit("Peoria County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Adams"))
            .then(pl.lit("Adams County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Dupage"))
            .then(pl.lit("Dupage County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Kane"))
            .then(pl.lit("Kane County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Lake County"))
            .then(pl.lit("Lake County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Sangamon"))
            .then(pl.lit("Sangamon County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Vill County"))
            .then(pl.lit("Will County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Williamson"))
            .then(pl.lit("Williamson County Jail"))
            .when(pl.col("Cleaned Facility Name").str.contains("Winnebago"))
            .then(pl.lit("Williamson County Jail"))
            .otherwise(pl.col("Cleaned Facility Name"))
            .alias("Cleaned Facility Name")
        )
        
        # Load geocoded database
        if not self.geocoded_db_path.exists():
            raise FileNotFoundError(f"Geocoded database not found: {self.geocoded_db_path}")
        
        self.geocoded_db_df = pl.read_parquet(self.geocoded_db_path)
        print(f"   Loaded {len(self.geocoded_db_df)} geocoded facilities")
        
        return self.cleaned_data_df, self.geocoded_db_df
    
    def create_occurrence_analysis_charts(self) -> List[str]:
        """Create occurrence analysis charts matching the presentation style."""
        print("Creating occurrence analysis charts...")
        
        if self.cleaned_data_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        chart_files = []
        
        # 1. Most Common Occurrences (matching presentation style)
        total_occurrence_result = (
            self.cleaned_data_df
            .with_columns(
                pl.col("Cleaned Occurrences").str.split("; ").alias("Cleaned Occurrences")
            )
            .explode("Cleaned Occurrences")
            .filter(pl.col("Cleaned Occurrences").is_not_null())
            .select(
                pl.col("Cleaned Occurrences").value_counts(sort=True)
            )
            .unnest("Cleaned Occurrences")
            .head(12)
        )
        
        total_occurrence_result = total_occurrence_result.filter(
            ~pl.col("Cleaned Occurrences").is_in(["Error, no occurrence found"])
        )
        
        # Convert to pandas for Altair
        occurrence_df = total_occurrence_result.to_pandas()
        
        # Create the chart matching presentation style
        occurrence_chart = alt.Chart(occurrence_df).mark_bar(
            color="#E0AC3BA6"
        ).encode(
            x=alt.X('count:Q', title='Number of Cases'),
            y=alt.Y('Cleaned Occurrences:N', sort='-x', title='Occurrence'),
            tooltip=[
                alt.Tooltip('Cleaned Occurrences:N', title='Occurrence'),
                alt.Tooltip('count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=600,
            height=400,
            title='Most Common Occurrences Across All Jails'
        )
        
        # Add footnote
        footnote = alt.Chart(pd.DataFrame({
            "text": ["Note: Occurrences may be concurrent. Missing 2,027 Occurrences (7.3%)"],
            "x": [0],
            "y": [0]
        })).mark_text(
            align="left",
            baseline="bottom",
            fontSize=10,
            dx=0,
            dy=20,
            color="gray"
        ).encode(
            x=alt.value(-50),
            y=alt.value(440),
            text="text:N"
        )
        
        # Layer chart and footnote
        final_chart = alt.layer(
            occurrence_chart,
            footnote
        ).configure_view(
            stroke=None
        )
        
        # Save chart
        chart_file = self.output_dir / "occurrence_analysis.html"
        final_chart.save(str(chart_file))
        chart_files.append(str(chart_file))
        
        # 2. Top Facilities by Case Count
        top_facilities = (
            self.cleaned_data_df
            .filter(pl.col('Cleaned Facility Name').is_not_null())
            .group_by('Cleaned Facility Name')
            .len()
            .sort('len', descending=True)
            .head(20)
            .rename({'len': 'Case Count'})
        )
        
        facilities_chart = alt.Chart(top_facilities.to_pandas()).mark_bar(
            color="#da746d"
        ).encode(
            x=alt.X('Case Count:Q', title='Number of Cases'),
            y=alt.Y('Cleaned Facility Name:N', sort='-x', title='Facility Name'),
            tooltip=[
                'Cleaned Facility Name:N', 
                alt.Tooltip('Case Count:Q', format=',d')
            ]
        ).properties(
            width=600,
            height=400,
            title='Top 20 Facilities by Number of Cases'
        )
        
        facilities_file = self.output_dir / "top_facilities.html"
        facilities_chart.save(str(facilities_file))
        chart_files.append(str(facilities_file))
        
        # 3. Time Series Analysis
        time_series_data = (
            self.cleaned_data_df
            .filter(pl.col('Cleaned Date').is_not_null())
            .with_columns(
                pl.col('Cleaned Date').str.to_date("%m/%d/%Y").alias('Date_parsed')
            )
            .filter(pl.col('Date_parsed').dt.year().is_between(2018, 2024))
            .with_columns(
                pl.col('Date_parsed').dt.truncate('1mo').alias('Month')
            )
            .group_by('Month')
            .len()
            .sort('Month')
            .rename({'len': 'Case Count'})
        )
        
        time_series_chart = alt.Chart(time_series_data.to_pandas()).mark_line(
            point=True,
            strokeWidth=2,
            color="#50a0d9"
        ).encode(
            x=alt.X('Month:T', 
                    title='Date of Occurrence',
                    axis=alt.Axis(format='%b %Y')
            ),
            y=alt.Y('Case Count:Q', title='Number of Cases'),
            tooltip=[
                alt.Tooltip('Month:T', format='%B %d, %Y', title='Date'),
                alt.Tooltip('Case Count:Q', title='Cases')
            ]
        ).properties(
            width=700,
            height=400,
            title='Cases Over Time - Date of Occurrence'
        )
        
        time_series_file = self.output_dir / "time_series.html"
        time_series_chart.save(str(time_series_file))
        chart_files.append(str(time_series_file))
        
        # 4. Restraint Usage Analysis
        pattern = r"\bRestraints\b"
        restraints_table = self.cleaned_data_df.filter(
            pl.col("Cleaned Occurrences").str.contains(pattern)
        )
        
        restraints_table = (
            restraints_table.select(
                pl.col("Cleaned Facility Name").value_counts(sort=True)
            )
            .unnest("Cleaned Facility Name")
            .head(21)
        )
        
        restraints_table = restraints_table.filter(pl.col("Cleaned Facility Name") != "")
        
        restraints_chart = alt.Chart(restraints_table.to_pandas()).mark_bar(
            color="#5a8664"
        ).encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("Cleaned Facility Name:N", title="Jail").sort('-x'),
            tooltip=[
                alt.Tooltip("Cleaned Facility Name:N", title="Jail"),
                alt.Tooltip("count:Q", format=",d", title="Case Count")
            ]
        ).properties(
            width=600,
            height=400,
            title="Top Jails for Restraint Usage"
        )
        
        # Add footnote
        restraint_footnote = alt.Chart(pd.DataFrame({
            "text": ["Note: Missing 1,119 County Names (4.33%)"],
            "x": [0],
            "y": [0]
        })).mark_text(
            align="left",
            baseline="bottom",
            fontSize=10,
            dx=0,
            dy=20,
            color="gray"
        ).encode(
            x=alt.value(0),
            y=alt.value(440),
            text="text:N"
        )
        
        final_restraints_chart = alt.layer(
            restraints_chart,
            restraint_footnote
        ).configure_view(
            stroke=None
        )
        
        restraints_file = self.output_dir / "restraints_usage.html"
        final_restraints_chart.save(str(restraints_file))
        chart_files.append(str(restraints_file))
        
        print(f"   Created {len(chart_files)} occurrence analysis charts")
        return chart_files
    
    def create_facility_coverage_charts(self) -> List[str]:
        """Create facility coverage analysis charts."""
        print("Creating facility coverage charts...")
        
        if self.cleaned_data_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        chart_files = []
        
        # Facility coverage by months
        facility_coverage = (
            self.cleaned_data_df
            .filter(
                pl.col('Cleaned Date').is_not_null() &
                pl.col('Cleaned Facility Name').is_not_null()
            )
            .with_columns(
                pl.col('Cleaned Date').str.to_date("%m/%d/%Y").alias('Date_parsed')
            )
            .filter(pl.col('Date_parsed').dt.year().is_between(2018, 2024))
            .with_columns(
                pl.col('Date_parsed').dt.truncate('1mo').alias('Month_Year')
            )
            .group_by(['Cleaned Facility Name', 'Month_Year'])
            .len()
            .group_by('Cleaned Facility Name')
            .agg([
                pl.col('Month_Year').n_unique().alias('Months_With_Data'),
                pl.col('len').sum().alias('Total_Records')
            ])
            .sort(['Months_With_Data', 'Total_Records'], descending=True)
        )
        
        top20 = facility_coverage.head(15)
        
        coverage_chart = alt.Chart(top20.to_pandas()).mark_bar(opacity=0.8).encode(
            x=alt.X('Months_With_Data:Q', title='Months Covered (2018-2024)'),
            y=alt.Y('Cleaned Facility Name:N', sort='-x', title='Facility'),
            color=alt.Color('Months_With_Data:Q', 
                          scale=alt.Scale(scheme='redpurple', reverse=True), 
                          legend=alt.Legend(title="Months Covered")),
            tooltip=[
                alt.Tooltip('Cleaned Facility Name:N', title='Facility'),
                alt.Tooltip('Months_With_Data:Q', title='Months Covered'),
                alt.Tooltip('Total_Records:Q', title='Total Records')
            ]
        ).properties(
            width=600,
            height=400,
            title='Top 15 Facilities by Months Covered (2018-2024)'
        )
        
        coverage_file = self.output_dir / "facility_coverage.html"
        coverage_chart.save(str(coverage_file))
        chart_files.append(str(coverage_file))
        
        # Yearly heatmap for top facilities
        top20_names = top20['Cleaned Facility Name'].to_list()
        
        facility_year_df = (
            self.cleaned_data_df
            .filter(
                pl.col('Cleaned Date').is_not_null() &
                pl.col('Cleaned Facility Name').is_not_null()
            )
            .with_columns(
                pl.col('Cleaned Date').str.to_date("%m/%d/%Y").alias('Date_parsed')
            )
            .filter(pl.col('Date_parsed').dt.year().is_between(2018, 2024))
            .with_columns(
                pl.col('Date_parsed').dt.year().alias('Year')
            )
            .group_by(['Cleaned Facility Name', 'Year'])
            .len()
            .sort('len', descending=True)
            .to_pandas()
        )
        
        # Filter to top facilities
        facility_year_df = facility_year_df[facility_year_df['Cleaned Facility Name'].isin(top20_names)]
        
        heatmap_chart = alt.Chart(facility_year_df).mark_rect().encode(
            y=alt.Y('Cleaned Facility Name:N', sort=top20_names, title='Facility'),
            x=alt.X('Year:O', title='Year'),
            color=alt.Color('len:Q', title='Reports', scale=alt.Scale(scheme='magma')),
            tooltip=[
                alt.Tooltip('Cleaned Facility Name:N', title='Facility'),
                alt.Tooltip('Year:O', title='Year'),
                alt.Tooltip('len:Q', title='Reports')
            ]
        ).properties(
            width=500,
            height=400,
            title='Yearly Report Coverage for Top 15 Facilities'
        )
        
        heatmap_file = self.output_dir / "facility_heatmap.html"
        heatmap_chart.save(str(heatmap_file))
        chart_files.append(str(heatmap_file))
        
        print(f"   Created {len(chart_files)} facility coverage charts")
        return chart_files
    
    def create_interactive_map(self) -> str:
        """Create an interactive map showing jail facilities and incidents."""
        print("Creating interactive map...")
        
        if self.cleaned_data_df is None or self.geocoded_db_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Get matched records with coordinates (simplified matching for demo)
        matched_records = self.cleaned_data_df.filter(
            pl.col("Cleaned Facility Name").is_not_null()
        )
        
        if len(matched_records) == 0:
            print("   No records with facility names found")
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
        
        # Add incident clusters (simplified - just show facility locations)
        from folium.plugins import MarkerCluster
        
        incident_cluster = MarkerCluster(name='Jail Incidents')
        
        # Group incidents by facility and add markers
        facility_counts = matched_pandas['Cleaned Facility Name'].value_counts()
        
        for facility_name, count in facility_counts.head(20).items():
            # Find matching geocoded facility
            matching_facility = facilities_pandas[
                facilities_pandas['name'].str.contains(facility_name.split()[0], case=False, na=False)
            ]
            
            if not matching_facility.empty:
                facility = matching_facility.iloc[0]
                folium.CircleMarker(
                    location=[facility['latitude'], facility['longitude']],
                    radius=min(max(count / 10, 3), 15),  # Scale radius by count
                    popup=f"""
                    <b>{facility_name}</b><br>
                    Incident Count: {count:,}<br>
                    Type: {facility.get('facility_type', 'Unknown')}<br>
                    County: {facility.get('county', 'Unknown')}
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
        
        print(f"   Interactive map created: {map_file}")
        return str(map_file)
    
    def create_summary_dashboard(self) -> str:
        """Create a comprehensive summary dashboard."""
        print("Creating summary dashboard...")
        
        if self.cleaned_data_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Calculate summary statistics
        total_records = len(self.cleaned_data_df)
        
        # Count by facility
        facility_counts = self.cleaned_data_df.group_by("Cleaned Facility Name").len().sort("len", descending=True)
        top_facilities = facility_counts.head(10)
        
        # Count by occurrence type
        occurrence_counts = (
            self.cleaned_data_df
            .with_columns(
                pl.col("Cleaned Occurrences").str.split("; ").alias("Cleaned Occurrences")
            )
            .explode("Cleaned Occurrences")
            .filter(pl.col("Cleaned Occurrences").is_not_null())
            .group_by("Cleaned Occurrences")
            .len()
            .sort("len", descending=True)
            .head(10)
        )
        
        # Injury and death statistics
        injury_stats = self.cleaned_data_df.group_by("Injuries?").len()
        death_stats = self.cleaned_data_df.group_by("Resulting Death?").len()
        
        # Create HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Illinois Jail Data Dashboard - Altair Style</title>
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
                .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Illinois Jail Data Dashboard</h1>
                    <p>Comprehensive Analysis of Jail Incidents and Facilities (Altair Style)</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_records:,}</div>
                        <div class="stat-label">Total Records</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{facility_counts.height}</div>
                        <div class="stat-label">Unique Facilities</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(self.cleaned_data_df.filter(pl.col('Cleaned Date').is_not_null())):,}</div>
                        <div class="stat-label">Records with Dates</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(self.cleaned_data_df.filter(pl.col('Resulting Death?') == 'Yes')):,}</div>
                        <div class="stat-label">Confirmed Deaths</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Top Facilities by Incident Count</h2>
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
            facility_name = row.get('Cleaned Facility Name', 'Unknown')
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
        
        for i, row in enumerate(occurrence_counts.iter_rows(named=True), 1):
            occurrence = row.get('Cleaned Occurrences', 'Unknown')
            count = row.get('len', 0)
            html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{occurrence}</td>
                                <td>{count:,}</td>
                            </tr>
            """
        
        html_content += f"""
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Data Source: Illinois Jail Reports Database (Cleaned)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save dashboard
        dashboard_file = self.output_dir / "summary_dashboard.html"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"   Summary dashboard created: {dashboard_file}")
        return str(dashboard_file)
    
    def create_dashboard_index(self, chart_files: List[str], map_file: str, summary_file: str) -> str:
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
                    <h1>Illinois Jail Data Dashboard</h1>
                    <p>Comprehensive Analysis and Visualization of Jail Incidents (Altair Style)</p>
                </div>
                
                <div class="section">
                    <h2>Main Dashboard</h2>
                    <div class="link-grid">
                        <div class="link-card">
                            <a href="summary_dashboard.html">
                                <h3>Summary Dashboard</h3>
                                <p>Overview statistics, top facilities, and occurrence types</p>
                            </a>
                        </div>
                        <div class="link-card">
                            <a href="illinois_jail_map.html">
                                <h3>Interactive Map</h3>
                                <p>Geographic visualization of facilities and incidents</p>
                            </a>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Analysis Charts (Vega-Altair)</h2>
                    <div class="link-grid">
        """
        
        chart_names = {
            'occurrence_analysis.html': '📋 Occurrence Analysis',
            'top_facilities.html': 'Top Facilities',
            'time_series.html': '📅 Time Series',
            'restraints_usage.html': 'Restraint Usage',
            'facility_coverage.html': 'Facility Coverage',
            'facility_heatmap.html': '🔥 Facility Heatmap'
        }
        
        for chart_file in chart_files:
            chart_name = Path(chart_file).name
            display_name = chart_names.get(chart_name, chart_name)
            html_content += f"""
                        <div class="link-card">
                            <a href="{chart_name}">
                                <h3>{display_name}</h3>
                                <p>Interactive Vega-Altair visualizations</p>
                            </a>
                        </div>
            """
        
        html_content += f"""
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Data Source: Illinois Jail Reports Database (Cleaned)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        index_file = self.output_dir / "index.html"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"   Index page created: {index_file}")
        return str(index_file)
    
    def create_comprehensive_dashboard(self) -> Dict[str, str]:
        """Create all dashboard components using Altair style."""
        print("🚀 Creating Comprehensive Illinois Jail Dashboard (Altair Style)")
        print("=" * 65)
        
        # Load data
        cleaned_data, geocoded_db = self.load_data()
        
        # Create all components
        dashboard_files = {}
        
        # 1. Occurrence analysis charts
        occurrence_charts = self.create_occurrence_analysis_charts()
        dashboard_files['occurrence_charts'] = occurrence_charts
        
        # 2. Facility coverage charts
        coverage_charts = self.create_facility_coverage_charts()
        dashboard_files['coverage_charts'] = coverage_charts
        
        # 3. Interactive map
        map_file = self.create_interactive_map()
        if map_file:
            dashboard_files['map'] = map_file
        
        # 4. Summary dashboard
        summary_file = self.create_summary_dashboard()
        dashboard_files['summary'] = summary_file
        
        # 5. Create index page
        all_charts = occurrence_charts + coverage_charts
        index_file = self.create_dashboard_index(all_charts, map_file, summary_file)
        dashboard_files['index'] = index_file
        
        print(f"\nDashboard created successfully!")
        print(f"   Output directory: {self.output_dir}")
        print(f"   Components created: {len(dashboard_files)}")
        
        return dashboard_files

def create_illinois_jail_altair_dashboard():
    """Main function to create the Illinois jail dashboard with Altair style."""
    print("🚀 Illinois Jail Dashboard Creator (Altair Style)")
    print("=" * 50)
    
    # Initialize dashboard creator
    dashboard = IllinoisJailAltairDashboard()
    
    # Create comprehensive dashboard
    dashboard_files = dashboard.create_comprehensive_dashboard()
    
    print(f"\nDashboard creation completed!")
    print(f"   All files saved to: {dashboard.output_dir}")
    print(f"   Open index.html in your browser to view the dashboard")
    
    return dashboard, dashboard_files

if __name__ == "__main__":
    dashboard, files = create_illinois_jail_altair_dashboard()
    print("\nDashboard creation completed successfully!")
