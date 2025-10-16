import click
from pathlib import Path
import pickle
import time
import polars as pl
from cleaning.clean_database import main as clean_database_main
from utils_main import process_all_pdfs, export_parquets_excel
from handwritten.handwritten_processor import process_handwritten_only, get_handwritten_statistics

@click.command()
@click.option("--mode",
              type=click.Choice(['full', 'sample', 'debug', 'handwritten', 'geocode', 'illinois-db', 'map', 'dashboard', 'altair-dashboard']),
              default = 'full',
              help = 'Processing mode: full (all data 27,800 pages), sample (aprox 642 pages), debug (few problematic pages), handwritten (only handwritten documents), geocode (geocode addresses), illinois-db (build Illinois jail database), map (create interactive maps), dashboard (create comprehensive dashboard), altair-dashboard (create Altair-style dashboard)')
@click.option("--step",
              type=click.Choice(['all', 'parse', 'clean', 'export', 'handwritten', 'geocode', 'illinois-db', 'map', 'dashboard', 'altair-dashboard']),
              default='all', help='Pipeline step: all (parse+clean+export), parse (only parse), clean (only clean), export (only export parquets to excel), handwritten (only handwritten analysis), geocode (geocode addresses), illinois-db (build Illinois jail database), map (create interactive maps), dashboard (create comprehensive dashboard), altair-dashboard (create Altair-style dashboard)')
def main(mode, step):
    """ Processing jail PDFs """
    click.echo(f"Running in {mode.upper()} mode")
    
    # project paths
    out_data = Path(__file__).parent / "data/jails-data/output"
    out_data.mkdir(parents=True, exist_ok=True)
    
    if mode == 'full':
        samples = Path(__file__).parent / "data/jails-data/raw"
        processed = Path(__file__).parent / "data/jails-data/processed"
        suffix = "_full"
    elif mode == "sample":
        samples = Path(__file__).parent / "data/jails-data/samples"
        processed = Path(__file__).parent / "data/jails-data/processed/big_samples"
        suffix = "_sample"
    elif mode == "debug":
        samples = Path(__file__).parent / "data/jails-data/samples/debug"
        processed = Path(__file__).parent / "data/jails-data/processed/debug_processed"
        suffix = "_debug"
    elif mode == "handwritten":
        # For handwritten mode, we work with existing parsed data
        samples = None
        processed = None
        suffix = "_handwritten"
    elif mode == "geocode" or mode == "illinois-db" or mode == "map" or mode == "dashboard" or mode == "altair-dashboard":
        # For geocoding, Illinois DB, mapping, and dashboard modes, we work with existing data
        samples = None
        processed = None
        suffix = ""
        
    # Create output file paths
    out_parquet = out_data / f"jails_pdfs{suffix}.parquet"
    log_parquet = out_data / f"processing_logs{suffix}.parquet"
    backup_file = out_data / f"jails_pdfs_backup{suffix}.pkl"
    out_parquet_cleaned = out_data / f"jails_pdfs_cleaned.parquet"
    out_parquet_persons = out_data / f"jails_person_records.parquet"
    
    # Final Excel database out path_
    out_excel_final = out_data / f"jails_database_with_links.xlsx"
    
    # Handwritten specific paths
    handwritten_dir = Path(__file__).parent / "data/jails-data/handwritten_party"
    handwritten_dir.mkdir(parents=True, exist_ok=True)
    handwritten_parquet = handwritten_dir / "handwritten_cleaned.parquet"
    handwritten_excel = handwritten_dir / "handwritten_documents.xlsx"
    
    # Time cloking
    start_time = time.time()
    
    if step in ['all', 'parse']: 
        # First parse all the pdfs and parrse images
        all_dicts_list, processing_logs = process_all_pdfs(samples, processed, dpi=300)
        
        # Save data as a pickle
        with open(backup_file, "wb") as f:
            pickle.dump(all_dicts_list, f)
        print(f"Saved backup to {backup_file}")
        
        df = pl.DataFrame(all_dicts_list)
        df.write_parquet(out_parquet)
        
        #log of errors
        log_df = pl.DataFrame(processing_logs)
        log_df.write_parquet(log_parquet)
        processing_time = time.time() - start_time
        
        # Summary 
        click.echo("\n" + "="*50)
        click.echo(f"Total pages attempted: {len(processing_logs)}")
        
    if step in ['all', 'clean']:
        click.echo("Running cleaning pipeline...")
        clean_database_main(out_parquet, out_parquet_cleaned, out_parquet_persons)
        processing_time = time.time() - start_time
    
    base_url = "https://uchicagoedu-my.sharepoint.com/personal/divijs_uchicago_edu/Documents/Jail reports data/"
    
    if step in ['all', 'export']:
        click.echo("Exporting to Excel with hyperlinks...")
        export_parquets_excel(out_parquet_cleaned, out_parquet_persons,out_excel_final , base_url)
        processing_time = time.time() - start_time
    
    if step == 'handwritten' or mode == 'handwritten':
        click.echo("Processing handwritten documents...")
        
        # Use raw data for handwritten processing
        full_parquet = out_data / "jails_pdfs_full.parquet"
        
        if not full_parquet.exists():
            click.echo(f" Error: {full_parquet} not found.")
            click.echo("Please run the full pipeline first to generate the raw data files.")
            return
        
        click.echo(f"✓ Using raw data: {full_parquet}")
        click.echo("Note: This will process only handwritten documents (OCR < 80)")
        
        # Get handwritten statistics from raw data
        stats = get_handwritten_statistics(full_parquet)
        click.echo(f"Handwritten documents: {stats['handwritten_documents']} out of {stats['total_documents']} ({stats['handwritten_percentage']:.2f}%)")
        
        # Process handwritten documents from raw data
        process_handwritten_only(full_parquet, handwritten_parquet, handwritten_excel, base_url)
        processing_time = time.time() - start_time
    
    if step == 'geocode' or mode == 'geocode':
        click.echo("Geocoding jail addresses...")
        
        # Import geocoding processor
        from geocoding.processor import JailAddressProcessor
        
        # Check if cleaned data exists
        cleaned_parquet = out_data / "jails_database_with_links.xlsx"
        if not cleaned_parquet.exists():
            click.echo(f"❌ Error: {cleaned_parquet} not found.")
            click.echo("Please run the cleaning step first to generate the cleaned data.")
            return
        
        click.echo(f"✓ Using cleaned data: {cleaned_parquet}")
        
        # Load the data
        df = pl.read_excel(cleaned_parquet)
        click.echo(f"📊 Loaded {len(df)} records")
        
        # Process addresses with Illinois geocoding
        processor = JailAddressProcessor()
        df_geocoded = processor.process_jail_addresses(df)
        
        # Export geocoded data
        geocoded_output = out_data / "jails_database_geocoded.parquet"
        processor.export_geocoded_data(df_geocoded, geocoded_output)
        
        # Get and display statistics
        stats = processor.get_processing_stats(df_geocoded)
        click.echo(f"\n📈 Geocoding Statistics:")
        click.echo(f"   Successfully Geocoded: {stats.get('successfully_geocoded', 0)}")
        click.echo(f"   Success Rate: {stats.get('success_rate', 0):.2%}")
        click.echo(f"   High Confidence Matches: {stats.get('high_confidence_matches', 0)}")
        click.echo(f"   Total Clusters: {stats.get('total_clusters', 0)}")
        
        processing_time = time.time() - start_time
        click.echo(f"Geocoding completed in {processing_time:.1f}s ({processing_time/60:.1f} min)")
    
    if step == 'illinois-db' or mode == 'illinois-db':
        click.echo("Building Illinois jail database...")
        
        # Import unified processor
        from geocoding.unified_processor import process_illinois_jail_data
        
        # Check if cleaned data exists
        cleaned_data_path = out_data / "jails_database_with_links.xlsx"
        if not cleaned_data_path.exists():
            click.echo(f"❌ Error: {cleaned_data_path} not found.")
            click.echo("Please run the cleaning step first to generate the cleaned data.")
            return
        
        click.echo(f"✓ Using cleaned data: {cleaned_data_path}")
        
        # Process all Illinois jail data
        results = process_illinois_jail_data(str(cleaned_data_path))
        
        click.echo(f"\n📊 Illinois Database Results:")
        click.echo(f"   Illinois Facilities: {len(results['illinois_database'])}")
        click.echo(f"   Geocoded: {len(results['illinois_database'].filter(pl.col('latitude').is_not_null()))}")
        click.echo(f"   Matched Records: {len(results['matched_data'].filter(pl.col('illinois_latitude').is_not_null()))}")
        click.echo(f"   Unified Database: {len(results['unified_database'])}")
        
        processing_time = time.time() - start_time
        click.echo(f"Illinois database building completed in {processing_time:.1f}s ({processing_time/60:.1f} min)")
    
    if step == 'map' or mode == 'map':
        click.echo("Creating interactive maps...")
        
        # Import mapping creators
        from mapping.folium_map import create_illinois_jail_maps
        from mapping.kepler_map import create_illinois_jail_kepler_maps
        from mapping.leaflet_map import create_illinois_jail_leaflet_maps
        
        # Check if Illinois database exists
        illinois_db_path = Path(__file__).parent / "data/illinois_jail_analysis/unified_illinois_jails.parquet"
        if not illinois_db_path.exists():
            click.echo(f"❌ Error: {illinois_db_path} not found.")
            click.echo("Please run the Illinois database step first.")
            return
        
        click.echo(f"✓ Using Illinois database: {illinois_db_path}")
        
        # Create interactive maps
        click.echo("Creating Folium maps...")
        folium_maps = create_illinois_jail_maps()
        
        click.echo("Creating Leaflet maps...")
        leaflet_maps = create_illinois_jail_leaflet_maps()
        
        click.echo("Creating Kepler.gl maps...")
        kepler_maps = create_illinois_jail_kepler_maps()
        
        all_maps = folium_maps + leaflet_maps + kepler_maps
        
        click.echo(f"\n🗺️ Created {len(all_maps)} interactive maps:")
        click.echo("   📁 Folium Maps:")
        for map_path in folium_maps:
            click.echo(f"      - {map_path}")
        click.echo("   📁 Leaflet Maps:")
        for map_path in leaflet_maps:
            click.echo(f"      - {map_path}")
        click.echo("   📁 Kepler.gl Maps:")
        for map_path in kepler_maps:
            click.echo(f"      - {map_path}")
        
        processing_time = time.time() - start_time
        click.echo(f"Map creation completed in {processing_time:.1f}s ({processing_time/60:.1f} min)")

    if step == 'dashboard' or mode == 'dashboard':
        click.echo("Creating comprehensive dashboard...")

        # Import dashboard components
        from dashboard.main_dashboard import main as dashboard_main

        # Run dashboard creation
        try:
            # Change to the correct directory for dashboard execution
            import os
            original_cwd = os.getcwd()
            os.chdir(Path(__file__).parent)
            
            dashboard_main.callback(step='all', force_rebuild=False)
            
            # Restore original directory
            os.chdir(original_cwd)
            
            processing_time = time.time() - start_time
            click.echo(f"Dashboard creation completed in {processing_time:.1f}s ({processing_time/60:.1f} min)")
        except Exception as e:
            click.echo(f"❌ Error creating dashboard: {e}")
            return

    if step == 'altair-dashboard' or mode == 'altair-dashboard':
        click.echo("Creating Altair-style dashboard...")

        # Import Altair dashboard components
        from dashboard.altair_dashboard_creator import create_illinois_jail_altair_dashboard

        # Run Altair dashboard creation
        try:
            # Change to the correct directory for dashboard execution
            import os
            original_cwd = os.getcwd()
            os.chdir(Path(__file__).parent)
            
            dashboard, files = create_illinois_jail_altair_dashboard()
            
            # Restore original directory
            os.chdir(original_cwd)
            
            processing_time = time.time() - start_time
            click.echo(f"Altair dashboard creation completed in {processing_time:.1f}s ({processing_time/60:.1f} min)")
        except Exception as e:
            click.echo(f"❌ Error creating Altair dashboard: {e}")
            return
    
    # Final timing
    click.echo(f"Processing time: {processing_time:.1f}s ({processing_time/60:.1f} min)")

if __name__ == "__main__":
    main()