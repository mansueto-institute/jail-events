import polars as pl

def reshape_to_long(df: pl.DataFrame, id_cols: list | str, list_col: str) -> pl.DataFrame:
    """
    Reshapes a DataFrame from wide to long by exploding a list column.
    Keeps specified ID columns and the newly exploded values.
    
    Args:
        df: The input Polars DataFrame.
        id_cols: A column name or list of column names to keep as identifiers.
        list_col: The name of the column containing lists to be exploded.
        
    Returns:
        A new DataFrame in long format.
    """
    # Ensure id_cols is a list for consistent processing
    if isinstance(id_cols, str):
        id_cols = [id_cols]
    
    print(f"Reshaping DataFrame by exploding column '{list_col}'...")
    # Select the necessary columns and then explode the list column
    reshaped_df = df.select(id_cols + [list_col]).explode(list_col)
    
    return reshaped_df

if __name__ == "__main__":
    # Create a sample DataFrame with a page_id to simulate real data
    test_df = pl.DataFrame({
        "page_id": ["page_1", "page_2", "page_3"],
        "Table Contents": [
            ["Cross, Anton Nelson", "| 02/04/1999", "Murder 1*, Agg Battery", "Smith, John"],
            ["Johnson, Mary Jane", "Gannon Andres", "This is not a name", "SHERIFF DEPT"],
            ['Camacho, Juan L1S1218','4/01/1995.','01/03/2021']
        ],
        "Source_File": ["file_A.pdf", "file_B.pdf", "file_C.pdf"]
    })

    print("--- Original DataFrame ---")
    print(test_df)

    # Reshape the data, keeping 'page_id' and 'Source_File' as identifiers
    long_df = reshape_to_long(test_df, id_cols=["page_id", "Source_File"], list_col="Table Contents")

    print("\n--- Reshaped (Long) DataFrame ---")
    print(long_df)
