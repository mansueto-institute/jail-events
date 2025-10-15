"""
Handwritten document evaluation and processing module.

This module provides functionality to:
1. Evaluate OCR confidence and identify handwritten documents (OCR < 80)
2. Create separate pipeline for handwritten documents only
3. Export handwritten documents with links to Excel
"""

import polars as pl
from pathlib import Path
from typing import List, Tuple
import pandas as pd
from xlsxwriter import Workbook


def evaluate_handwritten_documents(input_parquet: Path) -> pl.DataFrame:
    """
    Evaluate OCR confidence and identify handwritten documents.
    
    Args:
        input_parquet: Path to the input parquet file with OCR confidence data
        
    Returns:
        DataFrame with handwritten documents (OCR_Confidence < 80)
    """
    print("Evaluating handwritten documents...")
    
    # Read the parquet file
    df = pl.read_parquet(input_parquet)
    
    # Filter for handwritten documents (OCR confidence < 80)
    handwritten_df = df.filter(pl.col("OCR_Confidence") < 80)
    
    print(f"Found {len(handwritten_df)} handwritten documents out of {len(df)} total documents")
    print(f"Handwritten percentage: {len(handwritten_df) / len(df) * 100:.2f}%")
    
    return handwritten_df


def create_handwritten_excel(handwritten_df: pl.DataFrame, 
                            output_path: Path, 
                            base_url: str) -> None:
    """
    Create Excel file with handwritten documents using the same structure as jails_database_with_links.xlsx.
    Replicates the export_parquets_excel function but only for handwritten pages.
    
    Args:
        handwritten_df: DataFrame containing handwritten documents
        output_path: Path where to save the Excel file
        base_url: Base URL for creating hyperlinks to images
    """
    print(f"Creating Excel file for handwritten documents at: {output_path}")
    
    # Use the EXACT same column selection as export_parquets_excel (from utils_main.py lines 178-182)
    columns_to_export = [
        "Report ID", "Cleaned Facility Name", "Cleaned Address", "Zip Code", "Cleaned Date",
        "Cleaned Time of Day", "Cleaned Occurrences", "Injuries?", "Resulting Death?","Death Confidence", "Deceased Name",
        "Deceased Cause", "Deceased Date and Time", "Deceased on Suicide Watch", "Deceased Reporter", "Deceased Examined by Physician",
        "OCR_Confidence", "OCR_Word_Count", "Facility Name", "RD Number", "Phone Number", "Address", "Date",
        "Time of Day", "AM or PM", "Occurrence", "Table Contents"
    ]
    
    # Filter columns that exist in the dataframe
    available_columns = [col for col in columns_to_export if col in handwritten_df.columns]
    export_df = handwritten_df.select(available_columns)
    
    # Create Excel file with hyperlinks using the SAME approach as export_parquets_excel
    excel_formula = f'=HYPERLINK("{base_url}" & [@"Report ID"] & ".png?Web=1", "View Image")'
    
    with Workbook(output_path) as wb:
        # Use the same format as export_parquets_excel
        hyperlink_format = wb.add_format({
            'font_color': "#7070E3",
            'underline': True
        })
        
        # Write pages dataset to first sheet (same as export_parquets_excel but only handwritten)
        export_df.write_excel(
            workbook=wb,
            worksheet='Handwritten Documents',  # Different worksheet name for clarity
            formulas={"Image_Link": {
                "formula": f'=HYPERLINK("{base_url}" & [@Report ID] & ".png?Web=1", "View Image")',
                "return_dtype": pl.String}
            }
        )
    
    print(f"Excel file created successfully with {len(export_df)} handwritten documents")


def check_handwritten_cache_status(output_dir: Path) -> dict:
    """
    Check if handwritten processing has already been completed by examining existing files.
    Uses jails_person_records.parquet as the reference for what's been processed.
    
    Args:
        output_dir: Directory containing the output files
        
    Returns:
        Dictionary with cache status information
    """
    status = {
        "handwritten_parquet_exists": False,
        "handwritten_excel_exists": False,
        "person_records_exists": False,
        "raw_data_exists": False,
        "needs_full_pipeline": False,
        "handwritten_pages_missing": False
    }
    
    # Check for handwritten output files
    handwritten_parquet = output_dir / "handwritten_party" / "handwritten_cleaned.parquet"
    handwritten_excel = output_dir / "handwritten_party" / "handwritten_documents.xlsx"
    person_records = output_dir / "jails_person_records.parquet"
    raw_data = output_dir / "jails_pdfs_full.parquet"
    
    status["handwritten_parquet_exists"] = handwritten_parquet.exists()
    status["handwritten_excel_exists"] = handwritten_excel.exists()
    status["person_records_exists"] = person_records.exists()
    status["raw_data_exists"] = raw_data.exists()
    
    # Check if handwritten pages are missing from person records
    if status["person_records_exists"]:
        try:
            # Read person records to see what pages have been processed
            person_df = pl.read_parquet(person_records)
            processed_pages = set(person_df["Report ID"].unique())
            
            # Check if we have raw data to compare against
            if status["raw_data_exists"]:
                raw_df = pl.read_parquet(raw_data)
                all_pages = set(raw_df["Report ID"].unique())
                
                # Find handwritten pages (OCR < 80)
                handwritten_pages = set(
                    raw_df.filter(pl.col("OCR_Confidence") < 80)["Report ID"].unique()
                )
                
                # Check if handwritten pages are missing from person records
                missing_handwritten = handwritten_pages - processed_pages
                status["handwritten_pages_missing"] = len(missing_handwritten) > 0
                status["missing_count"] = len(missing_handwritten)
                status["total_handwritten"] = len(handwritten_pages)
                
                if status["handwritten_pages_missing"]:
                    status["reason"] = f"Found {len(missing_handwritten)} handwritten pages missing from person records"
                else:
                    status["reason"] = "All handwritten pages already processed"
            else:
                status["reason"] = "No raw data to compare against person records"
                
        except Exception as e:
            status["reason"] = f"Error reading person records: {str(e)}"
            status["handwritten_pages_missing"] = True
    else:
        status["reason"] = "No person records found - need to run full pipeline"
        status["needs_full_pipeline"] = True
    
    # Determine if we need to run full pipeline
    if not status["person_records_exists"]:
        status["needs_full_pipeline"] = True
        status["reason"] = "No person records found - need to run full pipeline"
    elif status["handwritten_pages_missing"]:
        status["needs_full_pipeline"] = False
        status["reason"] = f"Need to process {status['missing_count']} handwritten pages"
    elif status["handwritten_parquet_exists"] and status["handwritten_excel_exists"]:
        status["needs_full_pipeline"] = False
        status["reason"] = "Handwritten processing already completed"
    else:
        status["needs_full_pipeline"] = False
        status["reason"] = "Can process handwritten documents"
    
    return status


def process_handwritten_only(input_parquet: Path,
                           output_parquet: Path,
                           output_excel: Path,
                           base_url: str,
                           use_cleaned_cache: bool = True) -> None:
    """
    Process ALL handwritten documents from the raw data file.
    Simple approach: just process all handwritten pages (OCR < 80) and create Excel.
    Replicates the main pipeline cleaning steps but only for handwritten documents.
    
    Args:
        input_parquet: Path to input parquet file (should be raw data with all documents)
        output_parquet: Path to save cleaned handwritten parquet
        output_excel: Path to save Excel file with handwritten documents
        base_url: Base URL for hyperlinks
        use_cleaned_cache: Not used (kept for compatibility)
    """
    print("=== PROCESSING ALL HANDWRITTEN DOCUMENTS ===")
    
    # Check if output already exists
    if output_parquet.exists() and output_excel.exists():
        print("✅ Handwritten processing already completed!")
        print(f"   - Parquet: {output_parquet}")
        print(f"   - Excel: {output_excel}")
        return
    
    # Read raw data and filter for handwritten pages
    print(f"Reading raw data from: {input_parquet}")
    raw_df = pl.read_parquet(input_parquet)
    print(f"Total pages in raw data: {len(raw_df)}")
    
    # Find handwritten pages (OCR < 80)
    handwritten_pages = raw_df.filter(pl.col("OCR_Confidence") < 80)
    print(f"Handwritten pages (OCR < 80): {len(handwritten_pages)}")
    
    if len(handwritten_pages) == 0:
        print("No handwritten documents found in raw data!")
        return
    
    # Process all handwritten documents through cleaning pipeline
    from cleaning.clean_database import DatabaseCleaning, clean_occurrences
    
    print("Cleaning all handwritten documents...")
    df_to_clean = DatabaseCleaning(handwritten_pages)
    
    # Apply cleaning steps (same as main pipeline)
    print("  - Cleaning facility names...")
    df_to_clean.clean_facility_name()
    print("  - Cleaning addresses...")
    df_to_clean.clean_address()
    print("  - Extracting zip codes...")
    df_to_clean.get_zip_code()
    print("  - Cleaning dates...")
    df_to_clean.clean_date_occurrence()
    print("  - Cleaning phone numbers...")
    df_to_clean.clean_phone_number()
    print("  - Cleaning times...")
    df_to_clean.clean_time()
    print("  - Cleaning occurrences...")
    df_to_clean.df = df_to_clean.df.with_columns(
        pl.col("Occurrence").map_elements(clean_occurrences, return_dtype=pl.String).alias("Cleaned Occurrences")
    )
    print("  - Cleaning other occurrences...")
    df_to_clean.clean_other_occ()
    print("  - Combining counties...")
    df_to_clean.combine_counties()
    print("  - Extracting confident deaths...")
    df_to_clean.get_confident_deaths()
    
    # Save cleaned handwritten documents
    print(f"Saving cleaned handwritten documents to: {output_parquet}")
    df_to_clean.df.write_parquet(output_parquet)
    
    # Create Excel export with links (same structure as jails_database_with_links.xlsx)
    print(f"Creating Excel file with links: {output_excel}")
    create_handwritten_excel(df_to_clean.df, output_excel, base_url)
    
    print("✅ Handwritten processing completed!")
    print(f"   - Processed {len(df_to_clean.df)} handwritten documents")
    print(f"   - Parquet saved to: {output_parquet}")
    print(f"   - Excel saved to: {output_excel}")


def get_handwritten_statistics(input_parquet: Path) -> dict:
    """
    Get statistics about handwritten documents in the dataset.
    
    Args:
        input_parquet: Path to input parquet file
        
    Returns:
        Dictionary with handwritten statistics
    """
    df = pl.read_parquet(input_parquet)
    
    total_docs = len(df)
    handwritten_docs = len(df.filter(pl.col("OCR_Confidence") < 80))
    
    # OCR confidence statistics
    ocr_stats = df.select([
        pl.col("OCR_Confidence").min().alias("min_confidence"),
        pl.col("OCR_Confidence").max().alias("max_confidence"),
        pl.col("OCR_Confidence").mean().alias("avg_confidence"),
        pl.col("OCR_Confidence").median().alias("median_confidence")
    ]).to_dicts()[0]
    
    # Confidence distribution
    confidence_ranges = [
        (0, 20, "Very Low"),
        (20, 40, "Low"),
        (40, 60, "Medium"),
        (60, 80, "High"),
        (80, 100, "Very High")
    ]
    
    distribution = {}
    for min_conf, max_conf, label in confidence_ranges:
        count = len(df.filter(
            (pl.col("OCR_Confidence") >= min_conf) & 
            (pl.col("OCR_Confidence") < max_conf)
        ))
        distribution[label] = {
            "count": count,
            "percentage": count / total_docs * 100
        }
    
    return {
        "total_documents": total_docs,
        "handwritten_documents": handwritten_docs,
        "handwritten_percentage": handwritten_docs / total_docs * 100,
        "ocr_statistics": ocr_stats,
        "confidence_distribution": distribution
    }


if __name__ == "__main__":
    # Example usage
    input_file = Path("data/jails-data/output/jails_pdfs_full.parquet")
    output_file = Path("data/jails-data/handwritten_party/handwritten_cleaned.parquet")
    excel_file = Path("data/jails-data/handwritten_party/handwritten_documents.xlsx")
    base_url = "https://uchicagoedu-my.sharepoint.com/personal/divijs_uchicago_edu/Documents/Jail reports data/"
    
    if input_file.exists():
        process_handwritten_only(input_file, output_file, excel_file, base_url)
    else:
        print(f"Input file {input_file} not found!")
