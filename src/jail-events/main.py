import click
from pathlib import Path
import pickle
import time
import polars as pl
from cleaning.clean_database import main as clean_database_main
from utils_main import process_all_pdfs, export_parquets_excel

@click.command()
@click.option("--mode",
              type=click.Choice(['full', 'sample', 'debug']), 
              default = 'full',
              help = 'Processing mode: full (all data 27,800 pages), sample (aprox 642 pages), debug (few problematic pages)')
@click.option("--step", 
              type=click.Choice(['all', 'parse', 'clean', 'export']),
              default='all', help='Pipeline step: all (parse+clean+export), parse (only parse), clean (only clean), export (only export parquets to excel)')
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
        
    # Create output file paths
    out_parquet = out_data / f"jails_pdfs{suffix}.parquet"
    log_parquet = out_data / f"processing_logs{suffix}.parquet"
    backup_file = out_data / f"jails_pdfs_backup{suffix}.pkl"
    out_parquet_cleaned = out_data / f"jails_pdfs_cleaned.parquet"
    out_parquet_persons = out_data / f"jails_person_records.parquet"
    
    # Final Excel database out path_
    out_excel_final = out_data / f"jails_database_with_links.xlsx"
    
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
    # Final timing
    click.echo(f"Processing time: {processing_time:.1f}s ({processing_time/60:.1f} min)")

if __name__ == "__main__":
    main()