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
        person_id=pl.col("is_name").cum_sum()
    )

    # Step 2: Classify each row's information type (Name, DOB, Date, Charge).
    
    # Date patterns: YYYY or YY
    date_pattern = r"\d{1,2}[/\s]\s?\d{1,2}[/\s]\s?\d{2,4}"
    
    classified_df = df_with_person_id.with_columns(
        cleaned_for_date=pl.when(
            pl.col("is_name").not_() & pl.col("Table Contents").str.contains(date_pattern)
        )
        .then(
            pl.col("Table Contents")
            .str.replace_all(r"[|*,.]", "")
            .str.strip_chars()
        )
        .otherwise(None),
    ).with_columns(
        # Try multiple date formats using pl.coalesce
        parsed_date=pl.coalesce([
            # 4-digit years first (more specific)
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m/%d/%Y", strict=False),
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m %d %Y", strict=False),
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m/ %d/ %Y", strict=False),
            # 2-digit years second (less specific, but common)
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m/%d/%y", strict=False),
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m %d %y", strict=False),
            pl.col("cleaned_for_date").str.strptime(pl.Date, format="%m/ %d/ %y", strict=False)
        ]),
    ).with_columns(
        # Classify the info_type based on the parsing results
        info_type=pl.when(pl.col("is_name"))
        .then(pl.lit("Name"))
        .when(pl.col("parsed_date").dt.year() < 2005)
        .then(pl.lit("DOB"))
        .when(pl.col("parsed_date").is_not_null())
        .then(pl.lit("Date_Confined"))
        .otherwise(pl.lit("Arresting_Charge"))
    ).with_columns(
        # Use cleaned version for dates, original for everything else
        final_value=pl.when(pl.col("cleaned_for_date").is_not_null())
        .then(pl.col("cleaned_for_date"))  # Use cleaned version for dates
        .otherwise(pl.col("Table Contents"))  # Use original for names/charges
    )

    # Step 3: Pivot the data from long to wide format.
    pivoted_df = classified_df.pivot(
        index=["person_id", "page_id"],
        columns="info_type",
        values="final_value",
        aggregate_function="first"
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