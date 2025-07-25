
import polars as pl
from pathlib import Path
import jellyfish

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
        pl.col("your_column_name").str.extract(r"(\d{5})").alias("Zip Code")
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

def clean_occurrences(entries):

    actual_occurrences = ["Suicide (method)", "Suicide (attempt)", "Homicide", "Homicide Attempt", "Escape", "Escape Attempt",
                "Fire", "Serious Injury", "Battery", "Riot of Rebellion", "Sex Offense", "Assault on Staff",
                "Assault among Detainees", "Fighting among Detainees", "Restraints Used", "OC Spray Used", "Other (specify)"]
    
    if entries.is_empty():
        return ["Error, no occurrence found"]

    cleaned_list = []
    for term in entries:
        best_choice = None
        highest_jaro = 0.0
        for compare_term in actual_occurrences:
            jaro_score = jellyfish.jaro_similarity(term, compare_term)
            if jaro_score > highest_jaro:
                highest_jaro = jaro_score
                best_choice = compare_term

        if best_choice in ["Suicide (method)", "Suicide (attempt)", "Other (specify)"]:
            # Keep the original term (possibly has colon text, like "Other (specify): Fight")
            cleaned_list.append(term)
        else:
            if best_choice not in cleaned_list:
                cleaned_list.append(best_choice)

# Main assemble cleaning
def main():
    # Apply the cleaning
    out_path = Path(__file__).parent / 'data/jails-data/output'
    in_parquet = out_path / 'jails_pdfs.parquet'
    out_parquet = out_path / 'jails_pds_cleanned.parquet'
    # Cleaning
    df = divide_dataset(in_parquet)
    df_to_clean = DatabaseCleaning(df)

    df_to_clean.clean_facility_name()
    df_to_clean.clean_address()
    df_to_clean.get_zip_code()
    df_to_clean.clean_date_occurrence()
    df_to_clean.clean_phone_number()
    df_to_clean.clean_time()
    df_to_clean.df = df_to_clean.df.with_columns(pl.col("Occurrence").map_elements(clean_occurrences).alias("Cleaned Occurrences"))
    df_to_clean.clean_other_occ()
    df.write_parquet(out_parquet)

if __name__== "__main__":
    main()

"""
TO-DO
Death Statistics
"""