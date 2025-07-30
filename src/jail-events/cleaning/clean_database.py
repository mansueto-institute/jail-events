
import polars as pl
from pathlib import Path
import jellyfish
from .extract_names import identify_names_in_long_df
from .reshape_db import reshape_to_long
from .assemble_records import assemble_person_records

# 1. Divide the dataset with not handwritten and handwritten stuff
def divide_dataset(path_parquet):
    """
    Divide the dataset into handwritten and 
    """
    df = (pl.scan_parquet(path_parquet)
    .filter(pl.col("OCR_Confidence") > 80)
    .collect()
    )
    return df

class DatabaseCleaning:
    def __init__(self, df):
        self.df = df

    # 2. Cleaning of Facility names 
    def clean_facility_name(self):
        """Clean facility names using Polars expressions"""
        self.df = self.df.with_columns(
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

    #3. Cleaning address and grabbing the zipcode
    def clean_address(self):
        pattern = r"ss:"
        self.df = self.df.with_columns(
        pl.when(pl.col("Address").str.contains(pattern))
        .then(pl.col("Address").str.extract(r"s:\s*(\S.*)"))
        .otherwise(pl.col("Address"))
        .alias("Cleaned Address")
        )

    def get_zip_code(self):
        self.df = self.df.with_columns(
        pl.col("Address").str.extract(r"(\d{5})").alias("Zip Code")
        )

    # 4. Cleaning date of occurrence
    def clean_date_occurrence(self):
        self.df = self.df.with_columns(
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

    #5. Cleaning phone number
    def clean_phone_number(self):
        pattern = r"#:"
        self.df = self.df.with_columns(
        pl.when(pl.col("Phone Number").str.contains(pattern))
        .then(pl.col("Phone Number").str.extract(r"#\s*(\S.*)"))
        .otherwise(pl.col("Phone Number"))
        .alias("Phone Number")
        )

    #6. Basic clean of time
    def clean_time(self):
        pattern = r"Occurrence:"
        self.df = self.df.with_columns(
        pl.when(pl.col("Time of Day").str.contains(pattern))
        .then(pl.col("Time of Day").str.extract(r"e:\s*(\S.*)"))
        .otherwise(pl.col("Time of Day"))
        .alias("Cleaned Time of Day")
        )

    def clean_other_occ(self):
        pattern = r"specify"
        self.df = self.df.with_columns(
        pl.when(pl.col("Cleaned Occurrences").str.contains(pattern))
        .then(pl.col("Cleaned Occurrences").str.extract(r"\):\s*(\S.*)"))
        .otherwise(pl.col("Cleaned Occurrences"))
        .alias("Cleaned Occurrences")
        )

    #Extraction of names

    #9. Clean existing injuries

    def clean_injuries(self):
        pattern = r"ibe\)[;:]"
        self.df = self.df.with_columns(
        pl.when(pl.col("Injuries?").str.contains(pattern))
        .then(pl.col("Injuries?").str.extract(r"\)[;:]\s*(\S.*)"))
        .otherwise(pl.col("Injuries?"))
        .alias("Cleaned Injuries")
        )
    # 10. persons database
    def extract_person_records(self) -> pl.DataFrame:
        """
        Extract person-level records from Table Contents column.
        Returns a separate DataFrame with individual person records.
        """
        print("Extracting person-level records from Table Contents...")
        print("Available columns:", self.df.columns)
        # Filter rows that have Table Contents data
        df_with_contents = self.df.filter(
            pl.col("Table Contents").is_not_null() & 
            pl.col("Table Contents").list.len() > 0
        )
        
        if len(df_with_contents) == 0:
            print("No Table Contents data found for person extraction.")
            return pl.DataFrame()
        
        # Create a unique page_id for tracking
        df_with_page_id = df_with_contents.with_row_index("page_id")
        
        # Reshape to long format
        long_df = reshape_to_long(
            df_with_page_id, 
            id_cols=["page_id", "Report ID"], 
            list_col="Table Contents"
        )
        
        # Identify names using the ML model
        identified_df = identify_names_in_long_df(
            long_df,
            text_column="Table Contents",
            target_column="is_name",
            batch_size=1000  # Adjust based on your memory
        )
        
        # Assemble into structured person records
        person_records_df = assemble_person_records(identified_df)
        
        print(f"Extracted {len(person_records_df)} person records.")
        return person_records_df
    
    def combine_counties(self):
        self.df = self.df.with_columns(
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

def clean_occurrences(entries):

    actual_occurrences = ["Suicide (method)", "Suicide (attempt)", "Homicide", "Homicide Attempt", "Escape", "Escape Attempt",
                "Fire", "Serious Injury", "Battery", "Riot of Rebellion", "Sex Offense", "Assault on Staff",
                "Assault among Detainees", "Fighting among Detainees", "Restraints Used", "OC Spray Used", "Other (specify)"]
    
    if entries.is_empty():
        return "Error, no occurrence found"

    cleaned_list = []
    for term in entries:
        # Skip None or empty terms
        if term is None or str(term).strip() == "":
            continue
        
        best_choice = None
        highest_jaro = 0.0
        for compare_term in actual_occurrences:
            jaro_score = jellyfish.jaro_similarity(term, compare_term)
            if jaro_score > highest_jaro:
                highest_jaro = jaro_score
                best_choice = compare_term
        #Add with minim hreshold if found a good match
        if best_choice is not None and highest_jaro > 0.5:
            if best_choice in ["Suicide (method)", "Suicide (attempt)", "Other (specify)"]:
                # Keep the original term (possibly has colon text, like "Other (specify): Fight")
                cleaned_list.append(term)
            else:
                if best_choice not in cleaned_list:
                    cleaned_list.append(best_choice)
        else:
            # If no good match found, keep original term but clean it
            cleaned_term = str(term).strip()
            if cleaned_term and cleaned_term not in cleaned_list:
                cleaned_list.append(cleaned_term)
    
    return "; ".join(cleaned_list) if cleaned_list else "No occurrence found"

# Main assemble cleaning
def main(input_path = None):
    # Apply the cleaning
    if input_path is None:
        out_path = Path(__file__).parent.parent / 'data/jails-data/SERVER/new run/output'
        in_parquet = out_path / 'jails_pdfs_full.parquet'
    else:
        in_parquet = Path(input_path)
        out_path = in_parquet.parent
    
    out_parquet = out_path / 'jails_pdfs_cleanned.parquet'
    out_parquet_persons = out_path / 'jails_person_records.parquet'
    
    # Cleaning
    df = divide_dataset(in_parquet)
    df_to_clean = DatabaseCleaning(df)
    
    print("=== CLEANING MAIN DATABASE ===")
    df_to_clean.clean_facility_name()
    df_to_clean.clean_address()
    df_to_clean.get_zip_code()
    df_to_clean.clean_date_occurrence()
    df_to_clean.clean_phone_number()
    df_to_clean.clean_time()
    df_to_clean.df = df_to_clean.df.with_columns(
        pl.col("Occurrence").map_elements(clean_occurrences, return_dtype=pl.String).alias("Cleaned Occurrences")
    )
    df_to_clean.clean_other_occ()
    df_to_clean.df.write_parquet(out_parquet)
    
    print("\n=== EXTRACTING PERSON RECORDS ===")
    # Extract person-level records
    person_records = df_to_clean.extract_person_records()
    
    # Save person records database
    print(f"Saving person records database to: {out_parquet_persons}")
    person_records.write_parquet(out_parquet_persons)
    

if __name__ == "__main__":
    main()
