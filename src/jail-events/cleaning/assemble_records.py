import polars as pl

def assemble_person_records(long_df: pl.DataFrame) -> pl.DataFrame:
    """
    Transforms a long-format DataFrame into a structured, wide-format table
    with one row per person's record.

    Args:
        long_df: A DataFrame in long format with columns 'page_id', 'Table Contents',
                 and a boolean 'is_name' column.

    Returns:
        A new DataFrame where each row contains a person's name, DOB,
        date confined, and arresting charge.
    """
    print("Assembling person records from long format data...")

    # Step 1: Create a unique ID for each person's block of data.
    # The cumsum() on the boolean 'is_name' column creates a new group
    # every time it encounters 'True'. This is the key to grouping the data.
    df_with_person_id = long_df.with_columns(
        person_id=pl.col("is_name").cumsum()
    )

    # Step 2: Classify each row's information type (Name, DOB, Date, Charge).
    # We create two new columns: one for the classified type and one for the value.
    classified_df = df_with_person_id.with_columns(
        # First, try to parse any string into a date object.
        # This handles multiple common OCR formats. It will be null if parsing fails.
        parsed_date=pl.col("Table Contents").str.to_date(
            formats=["%m/%d/%Y", "%m/ %d/ %Y", "%m %d %Y"], strict=False
        ),
        # Keep the original text value for pivoting.
        value=pl.col("Table Contents")
    ).with_columns(
        # Now, use a series of conditions to determine the info_type.
        # The order of these 'when' conditions is important.
        info_type=pl.when(pl.col("is_name"))
        .then(pl.lit("Name"))
        .when(pl.col("parsed_date").dt.year() < 2005)
        .then(pl.lit("DOB"))
        .when(pl.col("parsed_date").is_not_null())
        .then(pl.lit("Date_Confined"))
        .otherwise(pl.lit("Arresting_Charge"))
    )

    # Step 3: Pivot the data from long to wide format.
    # We group by the person_id and page_id, using the 'info_type' for new
    # column names and the 'value' for the cell contents.
    pivoted_df = classified_df.pivot(
        index=["person_id", "page_id"],
        columns="info_type",
        values="value",
        aggregate_function="first" # Take the first value if there are duplicates
    )

    # Step 4: Clean up and select the final columns.
    # The pivot may create columns we don't need. We also drop the temporary person_id.
    final_cols = ["page_id", "Name", "DOB", "Date_Confined", "Arresting_Charge"]
    
    # Ensure all expected columns exist, filling with null if they don't
    for col_name in final_cols:
        if col_name not in pivoted_df.columns:
            pivoted_df = pivoted_df.with_columns(pl.lit(None).alias(col_name))

    final_df = pivoted_df.select(final_cols)

    print("Record assembly complete.")
    return final_df