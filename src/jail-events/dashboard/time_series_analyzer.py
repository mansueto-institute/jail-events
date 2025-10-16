"""
Time Series Analyzer for Illinois Jail Dashboard
Analyzes temporal patterns in jail occurrences and events.
"""

import polars as pl
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

class JailTimeSeriesAnalyzer:
    """
    Analyzes time-series patterns in jail occurrence data.
    """
    
    def __init__(self, linked_data_path: str = "data/illinois_jail_analysis/linked_jail_data.parquet"):
        self.linked_data_path = Path(linked_data_path)
        self.linked_data_df: Optional[pl.DataFrame] = None
        self.time_series_data: Optional[pl.DataFrame] = None
        
    def load_linked_data(self) -> pl.DataFrame:
        """Load the linked jail data."""
        if not self.linked_data_path.exists():
            raise FileNotFoundError(f"Linked data not found: {self.linked_data_path}")
        
        self.linked_data_df = pl.read_parquet(self.linked_data_path)
        print(f"📊 Loaded {len(self.linked_data_df)} linked records")
        
        return self.linked_data_df
    
    def clean_date(self, date_str: str) -> Optional[datetime]:
        """Clean and parse date string."""
        if not isinstance(date_str, str) or not date_str.strip():
            return None
        
        # Remove extra whitespace and common prefixes
        cleaned = date_str.strip()
        
        # Common date patterns
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})/(\d{1,2})/(\d{2})',  # MM/DD/YY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if len(groups[2]) == 2:  # Two-digit year
                            year = int("20" + groups[2]) if int(groups[2]) < 50 else int("19" + groups[2])
                        else:
                            year = int(groups[2])
                        
                        month = int(groups[0])
                        day = int(groups[1])
                        
                        # Handle different date formats
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        
                        return datetime(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def extract_time_components(self) -> pl.DataFrame:
        """Extract and clean time components from the data."""
        if self.linked_data_df is None:
            raise ValueError("Data not loaded. Call load_linked_data() first.")
        
        print("🕒 Extracting and cleaning time components...")
        
        # Clean dates
        df_with_dates = self.linked_data_df.with_columns([
            pl.col("Date").map_elements(self.clean_date, return_dtype=pl.Datetime).alias("cleaned_date")
        ])
        
        # Filter out records with valid dates
        valid_dates_df = df_with_dates.filter(pl.col("cleaned_date").is_not_null())
        
        print(f"   📅 Found {len(valid_dates_df)} records with valid dates")
        
        # Extract time components
        df_with_time_components = valid_dates_df.with_columns([
            pl.col("cleaned_date").dt.year().alias("year"),
            pl.col("cleaned_date").dt.month().alias("month"),
            pl.col("cleaned_date").dt.day().alias("day"),
            pl.col("cleaned_date").dt.weekday().alias("weekday"),
            pl.col("cleaned_date").dt.quarter().alias("quarter"),
            pl.col("cleaned_date").dt.strftime("%Y-%m").alias("year_month"),
            pl.col("cleaned_date").dt.strftime("%Y-%W").alias("year_week")
        ])
        
        self.time_series_data = df_with_time_components
        return df_with_time_components
    
    def analyze_occurrences_over_time(self) -> Dict[str, Any]:
        """Analyze occurrence patterns over time."""
        if self.time_series_data is None:
            raise ValueError("Time series data not prepared. Call extract_time_components() first.")
        
        print("📈 Analyzing occurrence patterns over time...")
        
        # Count occurrences by year
        yearly_counts = self.time_series_data.group_by("year").len().sort("year")
        
        # Count occurrences by month (across all years)
        monthly_counts = self.time_series_data.group_by("month").len().sort("month")
        
        # Count occurrences by year-month
        monthly_timeline = self.time_series_data.group_by("year_month").len().sort("year_month")
        
        # Count occurrences by weekday
        weekday_counts = self.time_series_data.group_by("weekday").len().sort("weekday")
        
        # Count occurrences by quarter
        quarterly_counts = self.time_series_data.group_by("quarter").len().sort("quarter")
        
        # Calculate trends
        yearly_trend = self._calculate_trend(yearly_counts, "year", "len")
        # For monthly timeline, we need to convert year_month to numeric for trend calculation
        monthly_timeline_numeric = monthly_timeline.with_columns([
            pl.col("year_month").str.split("-").list.get(0).cast(pl.Int32).alias("year_numeric"),
            pl.col("year_month").str.split("-").list.get(1).cast(pl.Int32).alias("month_numeric")
        ]).with_columns([
            (pl.col("year_numeric") * 12 + pl.col("month_numeric")).alias("time_numeric")
        ])
        monthly_trend = self._calculate_trend(monthly_timeline_numeric, "time_numeric", "len")
        
        return {
            "yearly_counts": yearly_counts.to_dicts(),
            "monthly_counts": monthly_counts.to_dicts(),
            "monthly_timeline": monthly_timeline.to_dicts(),
            "weekday_counts": weekday_counts.to_dicts(),
            "quarterly_counts": quarterly_counts.to_dicts(),
            "yearly_trend": yearly_trend,
            "monthly_trend": monthly_trend,
            "total_records": len(self.time_series_data),
            "date_range": {
                "start": self.time_series_data["cleaned_date"].min(),
                "end": self.time_series_data["cleaned_date"].max()
            }
        }
    
    def _calculate_trend(self, data: pl.DataFrame, x_col: str, y_col: str) -> Dict[str, float]:
        """Calculate simple linear trend."""
        if len(data) < 2:
            return {"slope": 0.0, "r_squared": 0.0}
        
        # Convert to pandas for easier calculation
        df_pandas = data.to_pandas()
        
        # Simple linear regression
        x = df_pandas[x_col].values
        y = df_pandas[y_col].values
        
        # Calculate slope and intercept
        n = len(x)
        sum_x = x.sum()
        sum_y = y.sum()
        sum_xy = (x * y).sum()
        sum_x2 = (x * x).sum()
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return {"slope": 0.0, "r_squared": 0.0}
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = ((y - y_pred) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared
        }
    
    def analyze_occurrence_types(self) -> Dict[str, Any]:
        """Analyze patterns in occurrence types."""
        if self.time_series_data is None:
            raise ValueError("Time series data not prepared. Call extract_time_components() first.")
        
        print("🔍 Analyzing occurrence types...")
        
        # Count by occurrence type
        occurrence_counts = self.time_series_data.group_by("Occurrence").len().sort("len", descending=True)
        
        # Count by facility type
        facility_type_counts = self.time_series_data.group_by("matched_facility_type").len().sort("len", descending=True)
        
        # Count by county
        county_counts = self.time_series_data.group_by("matched_county").len().sort("len", descending=True)
        
        # Count by injury status
        injury_counts = self.time_series_data.group_by("Injuries?").len().sort("len", descending=True)
        
        # Count by death status
        death_counts = self.time_series_data.group_by("Resulting Death?").len().sort("len", descending=True)
        
        return {
            "occurrence_counts": occurrence_counts.to_dicts(),
            "facility_type_counts": facility_type_counts.to_dicts(),
            "county_counts": county_counts.to_dicts(),
            "injury_counts": injury_counts.to_dicts(),
            "death_counts": death_counts.to_dicts()
        }
    
    def get_time_series_summary(self) -> Dict[str, Any]:
        """Get comprehensive time series summary."""
        if self.time_series_data is None:
            raise ValueError("Time series data not prepared. Call extract_time_components() first.")
        
        time_analysis = self.analyze_occurrences_over_time()
        occurrence_analysis = self.analyze_occurrence_types()
        
        return {
            "time_analysis": time_analysis,
            "occurrence_analysis": occurrence_analysis,
            "summary_stats": {
                "total_records": len(self.time_series_data),
                "unique_facilities": self.time_series_data["matched_facility_name"].n_unique(),
                "unique_counties": self.time_series_data["matched_county"].n_unique(),
                "date_span_days": (time_analysis["date_range"]["end"] - time_analysis["date_range"]["start"]).days,
                "avg_records_per_day": len(self.time_series_data) / max(1, (time_analysis["date_range"]["end"] - time_analysis["date_range"]["start"]).days)
            }
        }

def analyze_jail_time_series():
    """Main function to analyze jail time series data."""
    print("📈 Illinois Jail Time Series Analysis")
    print("=" * 45)
    
    # Initialize analyzer
    analyzer = JailTimeSeriesAnalyzer()
    
    # Load data
    linked_data = analyzer.load_linked_data()
    
    # Extract time components
    time_series_data = analyzer.extract_time_components()
    
    # Analyze patterns
    summary = analyzer.get_time_series_summary()
    
    # Print key findings
    print(f"\n📊 Key Findings:")
    print(f"   Total Records: {summary['summary_stats']['total_records']:,}")
    print(f"   Unique Facilities: {summary['summary_stats']['unique_facilities']}")
    print(f"   Unique Counties: {summary['summary_stats']['unique_counties']}")
    print(f"   Date Span: {summary['summary_stats']['date_span_days']} days")
    print(f"   Avg Records/Day: {summary['summary_stats']['avg_records_per_day']:.1f}")
    
    print(f"\n📅 Top Years:")
    for item in summary['time_analysis']['yearly_counts'][:5]:
        print(f"   {item['year']}: {item['len']:,} records")
    
    print(f"\n🏛️ Top Facility Types:")
    for item in summary['occurrence_analysis']['facility_type_counts'][:5]:
        if item['matched_facility_type']:
            print(f"   {item['matched_facility_type']}: {item['len']:,} records")
    
    print(f"\n🏘️ Top Counties:")
    for item in summary['occurrence_analysis']['county_counts'][:5]:
        if item['matched_county']:
            print(f"   {item['matched_county']}: {item['len']:,} records")
    
    return analyzer, summary

if __name__ == "__main__":
    analyzer, summary = analyze_jail_time_series()
    print("\n🎉 Time series analysis completed successfully!")
