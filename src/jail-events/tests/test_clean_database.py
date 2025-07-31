import polars as pl
from pathlib import Path
from cleaning.clean_database import DatabaseCleaning

def test_extract_person_records_pipeline():
    # Sample DataFrame similar to your extract_names test
    df = pl.DataFrame({
        "Report ID": ["page_1", "page_2", "page_3", "page_4"],
        "Table Contents": [
            ["Cross, Anton Nelson", "| 02/04/1999", "Murder 1*, Agg Battery", "Smith, John"],
            ["Johnson, Mary Jane", "Gannon Andres", "This is not a name", "SHERIFF DEPT"],
            ["Camacho, Juan L1S1218", "4/01/1995.", "01/03/2021"],
            ["Ordonez, Robert F.", "08/12/1981", "03/11/2021", "Violating Order of Protection"]
        ],
        "OCR_Confidence": [99, 98, 97, 96],
        "Facility Name": ["Test Jail"]*4,
        "Address": ["123 Main St"]*4,
        "Date": ["Date of Occurrence: 03/11/2021"]*4,
        "Phone Number": ["#: 555-1234"]*4,
        "Time of Day": ["Occurrence: 12:00 PM"]*4,
        "Occurrence": [["Assault on Staff"]]*4,
        "Injuries?": ["None"]*4
    })
    
    print([type(x) for x in df["Table Contents"]])

    # Run through the cleaning pipeline
    cleaner = DatabaseCleaning(df)
    cleaner.clean_facility_name()
    cleaner.clean_address()
    cleaner.get_zip_code()
    cleaner.clean_date_occurrence()
    cleaner.clean_phone_number()
    cleaner.clean_time()
    cleaner.df = cleaner.df.with_columns(
        pl.col("Occurrence").map_elements(lambda x: "; ".join(x), return_dtype=pl.String).alias("Cleaned Occurrences")
    )
    cleaner.clean_other_occ()
    
    print("\n--- Cleaned DataFrame ---")
    print(cleaner.df.select([
        "Report ID", "Table Contents", "Facility Name", "Date", "Phone Number", "Occurrence"
    ]))

    # Extract person records
    person_records = cleaner.extract_person_records()
    
    print("\n--- Extracted Person Records ---")
    print(person_records)

    # Assert Ordonez is present
    assert person_records.filter(pl.col("Name").str.contains("Ordonez")).height > 0