"""
Interactive Streamlit Dashboard for Illinois Jail Data
Maintains Vega-Altair aesthetics with real-time filtering capabilities.
"""

import streamlit as st
import polars as pl
import pandas as pd
import altair as alt
import folium
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime

# Enable vegafusion for better performance
alt.data_transformers.enable("vegafusion")

# Page config
st.set_page_config(
    page_title="Illinois Jail Events Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class IllinoisJailStreamlitDashboard:
    """
    Interactive Streamlit dashboard for Illinois jail data analysis.
    Maintains Altair aesthetics with real-time filtering.
    """
    
    def __init__(self):
        self.cleaned_data_path = Path("data/jails-data/output/jails_pdfs_cleaned.parquet")
        self.geocoded_db_path = Path("data/illinois_jail_analysis/unified_illinois_jails.parquet")
        self.cleaned_data_df: Optional[pl.DataFrame] = None
        self.geocoded_db_df: Optional[pl.DataFrame] = None
        
    def load_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Load cleaned data and geocoded database."""
        if self.cleaned_data_df is None:
            self.cleaned_data_df = pl.read_parquet(self.cleaned_data_path)
            
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
        
        if self.geocoded_db_df is None:
            self.geocoded_db_df = pl.read_parquet(self.geocoded_db_path)
        
        return self.cleaned_data_df, self.geocoded_db_df
    
    def create_sidebar_filters(self) -> Dict[str, Any]:
        """Create sidebar filters and return filter values."""
        st.sidebar.header("🔍 Filters")
        
        # Load data
        cleaned_data, geocoded_db = self.load_data()
        
        # Convert to pandas for easier filtering
        df = cleaned_data.to_pandas()
        
        # Get unique values for filters
        facilities = sorted(df['Cleaned Facility Name'].dropna().unique())
        occurrences = sorted(df['Cleaned Occurrences'].dropna().unique())
        
        # Parse occurrences (split by semicolon)
        all_occurrences = set()
        for occ in occurrences:
            if isinstance(occ, str):
                all_occurrences.update([o.strip() for o in occ.split(';') if o.strip()])
        all_occurrences = sorted([occ for occ in all_occurrences if occ and occ != 'Error, no occurrence found'])
        
        # Date range filter
        df['Cleaned Date'] = pd.to_datetime(df['Cleaned Date'], errors='coerce')
        min_date = df['Cleaned Date'].min()
        max_date = df['Cleaned Date'].max()
        
        date_range = st.sidebar.date_input(
            "📅 Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Facility filter
        selected_facilities = st.sidebar.multiselect(
            "🏛️ Facilities",
            options=facilities,
            default=facilities[:10] if len(facilities) > 10 else facilities,
            help="Select facilities to analyze"
        )
        
        # Occurrence filter
        selected_occurrences = st.sidebar.multiselect(
            "📋 Occurrence Types",
            options=all_occurrences,
            default=all_occurrences[:10] if len(all_occurrences) > 10 else all_occurrences,
            help="Select occurrence types to analyze"
        )
        
        # Injury filter
        injury_options = ['All', 'Yes', 'No', 'Unknown']
        selected_injury = st.sidebar.selectbox(
            "🩹 Injuries",
            options=injury_options,
            index=0
        )
        
        # Death filter
        death_options = ['All', 'Yes', 'No', 'Unknown']
        selected_death = st.sidebar.selectbox(
            "💀 Resulting Death",
            options=death_options,
            index=0
        )
        
        return {
            'date_range': date_range,
            'facilities': selected_facilities,
            'occurrences': selected_occurrences,
            'injury': selected_injury,
            'death': selected_death
        }
    
    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filters to the dataframe."""
        filtered_df = df.copy()
        
        # Ensure dates are datetime
        filtered_df['Cleaned Date'] = pd.to_datetime(filtered_df['Cleaned Date'], errors='coerce')
        
        # Date filter
        if len(filters['date_range']) == 2:
            start_date, end_date = filters['date_range']
            filtered_df = filtered_df[
                (filtered_df['Cleaned Date'] >= pd.Timestamp(start_date)) &
                (filtered_df['Cleaned Date'] <= pd.Timestamp(end_date))
            ]
        
        # Facility filter
        if filters['facilities']:
            filtered_df = filtered_df[filtered_df['Cleaned Facility Name'].isin(filters['facilities'])]
        
        # Occurrence filter
        if filters['occurrences']:
            occurrence_mask = filtered_df['Cleaned Occurrences'].str.contains(
                '|'.join(filters['occurrences']), 
                case=False, 
                na=False
            )
            filtered_df = filtered_df[occurrence_mask]
        
        # Injury filter
        if filters['injury'] != 'All':
            filtered_df = filtered_df[filtered_df['Injuries?'] == filters['injury']]
        
        # Death filter
        if filters['death'] != 'All':
            filtered_df = filtered_df[filtered_df['Resulting Death?'] == filters['death']]
        
        return filtered_df
    
    def create_summary_cards(self, filtered_df: pd.DataFrame) -> None:
        """Create summary cards showing key statistics."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📊 Total Records",
                value=f"{len(filtered_df):,}",
                delta=None
            )
        
        with col2:
            unique_facilities = filtered_df['Cleaned Facility Name'].nunique()
            st.metric(
                label="🏛️ Unique Facilities",
                value=f"{unique_facilities:,}",
                delta=None
            )
        
        with col3:
            injuries = len(filtered_df[filtered_df['Injuries?'] == 'Yes'])
            st.metric(
                label="🩹 Injuries",
                value=f"{injuries:,}",
                delta=None
            )
        
        with col4:
            deaths = len(filtered_df[filtered_df['Resulting Death?'] == 'Yes'])
            st.metric(
                label="💀 Deaths",
                value=f"{deaths:,}",
                delta=None
            )
    
    def create_main_visualization(self, filtered_df: pd.DataFrame, variable: str) -> None:
        """Create the main visualization based on selected variable."""
        if variable == "Occurrence Types":
            self.create_occurrence_chart(filtered_df)
        elif variable == "Facilities":
            self.create_facility_chart(filtered_df)
        elif variable == "Time Series":
            self.create_time_series_chart(filtered_df)
        elif variable == "Restraint Usage":
            self.create_restraint_chart(filtered_df)
        elif variable == "Injury Analysis":
            self.create_injury_chart(filtered_df)
        elif variable == "Death Analysis":
            self.create_death_chart(filtered_df)
    
    def create_occurrence_chart(self, df: pd.DataFrame) -> None:
        """Create occurrence analysis chart."""
        # Process occurrences (split by semicolon)
        occurrence_data = []
        for _, row in df.iterrows():
            if pd.notna(row['Cleaned Occurrences']):
                occurrences = [occ.strip() for occ in str(row['Cleaned Occurrences']).split(';')]
                for occ in occurrences:
                    if occ and occ != 'Error, no occurrence found':
                        occurrence_data.append({'Occurrence': occ})
        
        if not occurrence_data:
            st.warning("No occurrence data found for the selected filters.")
            return
        
        occurrence_df = pd.DataFrame(occurrence_data)
        occurrence_counts = occurrence_df['Occurrence'].value_counts().head(15).reset_index()
        occurrence_counts.columns = ['Occurrence', 'Count']
        
        chart = alt.Chart(occurrence_counts).mark_bar(
            color="#E0AC3BA6"
        ).encode(
            x=alt.X('Count:Q', title='Number of Cases'),
            y=alt.Y('Occurrence:N', sort='-x', title='Occurrence Type'),
            tooltip=[
                alt.Tooltip('Occurrence:N', title='Occurrence'),
                alt.Tooltip('Count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=700,
            height=500,
            title='Most Common Occurrence Types (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_facility_chart(self, df: pd.DataFrame) -> None:
        """Create facility analysis chart."""
        facility_counts = df['Cleaned Facility Name'].value_counts().head(20).reset_index()
        facility_counts.columns = ['Facility', 'Count']
        
        chart = alt.Chart(facility_counts).mark_bar(
            color="#da746d"
        ).encode(
            x=alt.X('Count:Q', title='Number of Cases'),
            y=alt.Y('Facility:N', sort='-x', title='Facility Name'),
            tooltip=[
                alt.Tooltip('Facility:N', title='Facility'),
                alt.Tooltip('Count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=700,
            height=500,
            title='Top Facilities by Case Count (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_time_series_chart(self, df: pd.DataFrame) -> None:
        """Create time series chart."""
        # Filter out invalid dates
        df_clean = df.dropna(subset=['Cleaned Date'])
        if df_clean.empty:
            st.warning("No valid date data found for the selected filters.")
            return
        
        # Group by month
        df_clean['Month'] = df_clean['Cleaned Date'].dt.to_period('M')
        monthly_counts = df_clean.groupby('Month').size().reset_index()
        monthly_counts.columns = ['Month', 'Count']
        monthly_counts['Month'] = monthly_counts['Month'].dt.to_timestamp()
        
        chart = alt.Chart(monthly_counts).mark_line(
            point=True,
            strokeWidth=2,
            color="#50a0d9"
        ).encode(
            x=alt.X('Month:T', title='Date'),
            y=alt.Y('Count:Q', title='Number of Cases'),
            tooltip=[
                alt.Tooltip('Month:T', format='%B %Y', title='Date'),
                alt.Tooltip('Count:Q', title='Cases')
            ]
        ).properties(
            width=700,
            height=400,
            title='Cases Over Time (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_restraint_chart(self, df: pd.DataFrame) -> None:
        """Create restraint usage chart."""
        restraint_data = df[df['Cleaned Occurrences'].str.contains('Restraints', case=False, na=False)]
        
        if restraint_data.empty:
            st.warning("No restraint data found for the selected filters.")
            return
        
        facility_counts = restraint_data['Cleaned Facility Name'].value_counts().head(15).reset_index()
        facility_counts.columns = ['Facility', 'Count']
        
        chart = alt.Chart(facility_counts).mark_bar(
            color="#5a8664"
        ).encode(
            x=alt.X('Count:Q', title='Number of Cases'),
            y=alt.Y('Facility:N', sort='-x', title='Facility'),
            tooltip=[
                alt.Tooltip('Facility:N', title='Facility'),
                alt.Tooltip('Count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=700,
            height=400,
            title='Restraint Usage by Facility (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_injury_chart(self, df: pd.DataFrame) -> None:
        """Create injury analysis chart."""
        injury_counts = df['Injuries?'].value_counts().reset_index()
        injury_counts.columns = ['Injury Status', 'Count']
        
        chart = alt.Chart(injury_counts).mark_bar(
            color="#e74c3c"
        ).encode(
            x=alt.X('Count:Q', title='Number of Cases'),
            y=alt.Y('Injury Status:N', sort='-x', title='Injury Status'),
            tooltip=[
                alt.Tooltip('Injury Status:N', title='Injury Status'),
                alt.Tooltip('Count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=700,
            height=300,
            title='Injury Analysis (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_death_chart(self, df: pd.DataFrame) -> None:
        """Create death analysis chart."""
        death_counts = df['Resulting Death?'].value_counts().reset_index()
        death_counts.columns = ['Death Status', 'Count']
        
        chart = alt.Chart(death_counts).mark_bar(
            color="#8e44ad"
        ).encode(
            x=alt.X('Count:Q', title='Number of Cases'),
            y=alt.Y('Death Status:N', sort='-x', title='Death Status'),
            tooltip=[
                alt.Tooltip('Death Status:N', title='Death Status'),
                alt.Tooltip('Count:Q', format=',d', title='Case Count')
            ]
        ).properties(
            width=700,
            height=300,
            title='Death Analysis (Filtered Data)'
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def create_interactive_map(self, filtered_df: pd.DataFrame) -> None:
        """Create interactive map with filtered data."""
        # Load geocoded data
        _, geocoded_db = self.load_data()
        geocoded_pandas = geocoded_db.to_pandas()
        
        # Filter out facilities with NaN coordinates
        geocoded_pandas = geocoded_pandas.dropna(subset=['latitude', 'longitude'])
        
        # Get facility counts from filtered data
        facility_counts = filtered_df['Cleaned Facility Name'].value_counts().reset_index()
        facility_counts.columns = ['Facility', 'Count']
        
        # Create base map
        m = folium.Map(
            location=[40.0, -89.0],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # Add facility markers
        facility_colors = {
            'county': 'blue',
            'municipal': 'green',
            'juvenile': 'orange',
            'state': 'red',
            'federal': 'purple'
        }
        
        markers_added = 0
        
        for _, facility in geocoded_pandas.iterrows():
            # Skip if coordinates are invalid
            if pd.isna(facility['latitude']) or pd.isna(facility['longitude']):
                continue
            
            color = facility_colors.get(facility.get('facility_type', 'unknown'), 'gray')
            
            # Check if this facility is in our filtered data
            facility_name = str(facility.get('name', ''))
            if not facility_name or len(facility_name.split()) == 0:
                continue
            
            facility_count = facility_counts[
                facility_counts['Facility'].str.contains(
                    facility_name.split()[0], 
                    case=False, 
                    na=False
                )
            ]['Count'].sum()
            
            if facility_count > 0:
                try:
                    folium.CircleMarker(
                        location=[float(facility['latitude']), float(facility['longitude'])],
                        radius=max(min(facility_count / 10, 20), 5),
                        popup=f"""
                        <b>{facility_name}</b><br>
                        Type: {facility.get('facility_type', 'Unknown')}<br>
                        County: {facility.get('county', 'Unknown')}<br>
                        Cases: {facility_count:,}
                        """,
                        color='black',
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(m)
                    markers_added += 1
                except (ValueError, TypeError) as e:
                    # Skip facilities with invalid coordinates
                    continue
        
        # Add legend
        if markers_added > 0:
            legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 200px; height: 150px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:12px; padding: 10px">
            <p><b>Facility Types</b></p>
            <p><i class="fa fa-circle" style="color:blue"></i> County</p>
            <p><i class="fa fa-circle" style="color:green"></i> Municipal</p>
            <p><i class="fa fa-circle" style="color:orange"></i> Juvenile</p>
            <p><i class="fa fa-circle" style="color:red"></i> State</p>
            <p><i class="fa fa-circle" style="color:purple"></i> Federal</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
        else:
            st.warning(f"⚠️ No facilities with valid geocoded locations found for the current filters.")
        
        # Display map
        st.components.v1.html(m._repr_html_(), height=500)
    
    def run_dashboard(self) -> None:
        """Run the main dashboard."""
        # Header
        st.title("🏛️ Illinois Jail Events Dashboard")
        st.markdown("Interactive analysis of jail incident reports with real-time filtering")
        
        # Load data
        cleaned_data, _ = self.load_data()
        df = cleaned_data.to_pandas()
        
        # Create sidebar filters
        filters = self.create_sidebar_filters()
        
        # Apply filters
        filtered_df = self.apply_filters(df, filters)
        
        # Show summary cards
        st.subheader("📊 Summary Statistics")
        self.create_summary_cards(filtered_df)
        
        # Main visualization section
        st.subheader("📈 Main Visualization")
        
        # Variable selection
        variable_options = [
            "Occurrence Types",
            "Facilities", 
            "Time Series",
            "Restraint Usage",
            "Injury Analysis",
            "Death Analysis"
        ]
        
        selected_variable = st.selectbox(
            "Select variable to analyze:",
            options=variable_options,
            index=0
        )
        
        # Create main visualization
        self.create_main_visualization(filtered_df, selected_variable)
        
        # Interactive map section
        st.subheader("🗺️ Geographic Analysis")
        st.markdown("Map showing facilities with incident counts based on current filters")
        
        self.create_interactive_map(filtered_df)
        
        # Data table section
        st.subheader("📋 Filtered Data")
        st.markdown(f"Showing {len(filtered_df):,} records matching the selected filters")
        
        # Show sample of filtered data
        display_columns = [
            'Cleaned Facility Name', 'Cleaned Date', 'Cleaned Occurrences', 
            'Injuries?', 'Resulting Death?', 'Report ID'
        ]
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_columns].head(100),
            use_container_width=True,
            height=400
        )

def main():
    """Main function to run the Streamlit dashboard."""
    dashboard = IllinoisJailStreamlitDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
