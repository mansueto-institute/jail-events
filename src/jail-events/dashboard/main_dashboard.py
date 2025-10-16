"""
Main Dashboard Runner for Illinois Jail Data
Orchestrates the entire dashboard creation process.
"""

import click
from pathlib import Path
import time
from typing import Dict, Any

from .data_linker import link_jail_data
from .time_series_analyzer import analyze_jail_time_series
from .dashboard_creator import create_illinois_jail_dashboard
from .altair_dashboard_creator import create_illinois_jail_altair_dashboard

@click.command()
@click.option("--step",
              type=click.Choice(['all', 'link', 'analyze', 'dashboard', 'altair-dashboard']),
              default='all',
              help='Dashboard step: all (complete pipeline), link (data linking only), analyze (time series only), dashboard (visualization only), altair-dashboard (Altair style visualization)')
@click.option("--force-rebuild",
              is_flag=True,
              help='Force rebuild of all components even if they exist')
def main(step: str, force_rebuild: bool):
    """
    Create comprehensive Illinois jail data dashboard.
    
    This command orchestrates the entire dashboard creation process:
    1. Links jail records with geocoded facilities
    2. Analyzes time series patterns
    3. Creates interactive visualizations and maps
    """
    start_time = time.time()
    
    print("🏛️ Illinois Jail Data Dashboard")
    print("=" * 40)
    print(f"Step: {step.upper()}")
    print(f"Force rebuild: {force_rebuild}")
    print()
    
    dashboard_files = {}
    
    try:
        if step in ['all', 'link']:
            print("🔗 Step 1: Data Linking")
            print("-" * 25)
            
            # Check if linked data already exists
            linked_data_path = Path("data/illinois_jail_analysis/linked_jail_data.parquet")
            if linked_data_path.exists() and not force_rebuild:
                print("✅ Linked data already exists. Skipping data linking.")
                print(f"   File: {linked_data_path}")
            else:
                linker, linked_data, stats = link_jail_data()
                dashboard_files['linker'] = linker
                dashboard_files['linked_data'] = linked_data
                dashboard_files['link_stats'] = stats
                print("✅ Data linking completed!")
            
            print()
        
        if step in ['all', 'analyze']:
            print("📈 Step 2: Time Series Analysis")
            print("-" * 30)
            
            # Check if analysis already exists
            analysis_path = Path("data/illinois_jail_analysis/time_series_analysis.json")
            if analysis_path.exists() and not force_rebuild:
                print("✅ Time series analysis already exists. Skipping analysis.")
                print(f"   File: {analysis_path}")
            else:
                analyzer, summary = analyze_jail_time_series()
                dashboard_files['analyzer'] = analyzer
                dashboard_files['time_series_summary'] = summary
                print("✅ Time series analysis completed!")
            
            print()
        
        if step in ['all', 'dashboard']:
            print("📊 Step 3: Dashboard Creation")
            print("-" * 30)
            
            # Check if dashboard already exists
            dashboard_dir = Path("data/illinois_jail_analysis/dashboard")
            if dashboard_dir.exists() and not force_rebuild:
                print("✅ Dashboard already exists. Skipping dashboard creation.")
                print(f"   Directory: {dashboard_dir}")
            else:
                dashboard, files = create_illinois_jail_dashboard()
                dashboard_files['dashboard'] = dashboard
                dashboard_files['dashboard_files'] = files
                print("✅ Dashboard creation completed!")
            
            print()
        
        if step == 'altair-dashboard':
            print("📊 Step 3: Altair Dashboard Creation")
            print("-" * 35)
            
            # Check if Altair dashboard already exists
            altair_dashboard_dir = Path("data/illinois_jail_analysis/altair_dashboard")
            if altair_dashboard_dir.exists() and not force_rebuild:
                print("✅ Altair dashboard already exists. Skipping dashboard creation.")
                print(f"   Directory: {altair_dashboard_dir}")
            else:
                dashboard, files = create_illinois_jail_altair_dashboard()
                dashboard_files['altair_dashboard'] = dashboard
                dashboard_files['altair_dashboard_files'] = files
                print("✅ Altair dashboard creation completed!")
            
            print()
        
        # Final summary
        processing_time = time.time() - start_time
        
        print("🎉 Dashboard Pipeline Completed Successfully!")
        print("=" * 50)
        print(f"⏱️  Total processing time: {processing_time:.1f}s ({processing_time/60:.1f} min)")
        
        # Show output locations
        print("\n📁 Output Files:")
        
        if step in ['all', 'link']:
            linked_data_path = Path("data/illinois_jail_analysis/linked_jail_data.parquet")
            if linked_data_path.exists():
                print(f"   🔗 Linked Data: {linked_data_path}")
        
        if step in ['all', 'analyze']:
            print(f"   📈 Time Series Analysis: data/illinois_jail_analysis/")
        
        if step in ['all', 'dashboard']:
            dashboard_dir = Path("data/illinois_jail_analysis/dashboard")
            if dashboard_dir.exists():
                print(f"   📊 Dashboard: {dashboard_dir}/index.html")
                
                # List dashboard components
                dashboard_files_list = list(dashboard_dir.glob("*.html"))
                if dashboard_files_list:
                    print("   📋 Dashboard Components:")
                    for file in sorted(dashboard_files_list):
                        print(f"      - {file.name}")
        
        print(f"\n🌐 Open the dashboard in your browser:")
        print(f"   file://{Path('data/illinois_jail_analysis/dashboard/index.html').absolute()}")
        
    except Exception as e:
        print(f"\n❌ Error during dashboard creation: {e}")
        raise click.ClickException(f"Dashboard creation failed: {e}")

if __name__ == "__main__":
    main()
