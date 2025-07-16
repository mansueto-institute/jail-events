
import polars as pl
import altair as alt
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
import json
import jellyfish
alt.data_transformers.enable("vegafusion")



root = Path('..')
parquet_path = root / 'data/jails-data/output/jails_pdfs.parquet'
df = pl.read_parquet(parquet_path)


# 1. Divide the dataset with not handwritten



# 2. Cleaning of Facility names 

def clean_facility_name(df):
    """Clean facility names using Polars expressions"""
    return df.with_columns(
        pl.col('Facility Name')
        # First, clean OCR artifacts
        .str.replace_all(r'\\n|\\\\|\\/', ' ') 
        .str.replace_all(r'\n', ' ')
        .str.replace_all(r'[\\\/]+', ' ')
        .str.replace_all(r'\s+', ' ') 
        .str.strip_chars()
        # Extract facility name after any variation of "Name:"
        .str.extract(r'cility Name:\s*(.+)', 1)
        # Additional cleanup of extracted names
        .str.replace_all(r'[^a-zA-Z\s\'-]', ' ')  # Keep only letters, spaces, apostrophes, hyphens
        .str.replace_all(r'\s+', ' ')  # Clean multiple spaces again
        .str.strip_chars()  # Final trim
        # Stop at any word ending in "ddres" and remove that word + everything after
        .str.replace_all(r'\s+(ddress|ddrace).*$', '')
        .str.replace_all(r"(?i)\bSheriff's\b", "Sheriffs")
        .str.to_titlecase()
        .alias('Cleaned Facility Name')
    )

# Apply the cleaning
df_cleaned = clean_facility_name(df)
df_cleaned['Facility Name', 'Cleaned Facility Name']


# Cleaning date of occurrence

def clean_date_occurrence(df):
    return df.with_columns(
        pl.col("Date")
          # OCR cleanup (keep forward slashes)
          .str.replace_all(r"\\n|\\\\", " ")
          .str.replace_all(r"\n", " ")
          .str.replace_all(r"\s+", " ")
          .str.strip_chars()
          # Extract the MM/DD/YYYY text
          .str.extract(r"Date of Occurrence:\s*([0-9]{1,2}/[0-9]{1,2}/(20[0-9]{2}))", 1)
          # Parse & re‐format to zero‐padded MM/DD/YYYY
          .str.strptime(pl.Date, "%m/%d/%Y", strict=False)
          .alias("temp_date")
    ).with_columns(
        # Only keep dates between 2000 and 2025, otherwise set to null
        pl.when(pl.col("temp_date").dt.year().is_between(2000, 2025))
        .then(pl.col("temp_date").dt.strftime("%m/%d/%Y"))
        .otherwise(None)
        .alias("Cleaned Date")
    ).drop("temp_date")

df_cleaned = clean_date_occurrence(df_cleaned)
df_cleaned.select(["Date","Cleaned Date"]).head(10)


# Extraction 