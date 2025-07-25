import polars as pl
import re
from tqdm import tqdm
from transformers import pipeline
import torch.cuda
ner_model = None
from reshape_db import reshape_to_long

def get_ner_model():
    """Initialization of NER model"""
    global ner_model
    if ner_model is None:
        ner_model = pipeline("ner", 
                          model="dbmdz/bert-large-cased-finetuned-conll03-english", 
                          aggregation_strategy="simple",
                          device=0 if torch.cuda.is_available() else -1)
        
        # ner_model = pipeline("ner", 
        #                    model="distilbert-base-cased",  # 268MB vs 1.33GB
        #                    aggregation_strategy="simple",
        #                    device=0 if torch.cuda.is_available() else -1)  # Use GPU if available
    return ner_model

# Function for extracting names from the polars columns 
def clean_element(element):
    """ Clean a str element"""
    if not isinstance(element, str) or not element.strip():
        return ""
    # Remove OCR artifacts and numbers
    cleaned = re.sub(r'[|\\/\n\t\r"]+', ' ', element)  # Remove OCR artifacts
    cleaned = re.sub(r'\d+', '', cleaned)  # Remove numbers
    cleaned = re.sub(r'[^\w\s,\'-]', '', cleaned)  # Keep only letters, spaces, commas, apostrophes, hyphens
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Clean multiple spaces
    
    return cleaned


def is_likely_name_candidate(text: str) -> bool:
    """A fast, rule-based pre-filter to exclude obvious non-names."""
    if not text or not text.strip() or len(text.split()) > 5 or len(text) < 3:
        return False

    exclusions = ['murder', 'battery', 'assault', 'theft', 'warrant', 'arson', 
                  'substance', 'controlled', 'aggravated', 'felony', 'misdemeanor', 'sheriff']
    if any(word in text.lower() for word in exclusions):
        return False
    return True

def identify_names_in_long_df(df: pl.DataFrame, text_column: str, 
                             target_column: str = 'is_name', batch_size: int = 1000) -> pl.DataFrame:
    """
    Takes a long-format DataFrame and adds a boolean column indicating 
    whether each row contains a person's name.
    
    Args:
        df: The input Polars DataFrame in long format
        text_column: The name of the column containing individual text strings
        target_column: The name for the new boolean column (default: 'is_name')
        batch_size: Number of rows to process at once
        
    Returns:
        DataFrame with an additional boolean column
    """
    ner = get_ner_model()
    n_rows = len(df)
    is_name_results = [False] * n_rows  # Initialize all as False
    
    print(f"Processing {n_rows} rows in batches of {batch_size}...")
    
    for start_idx in tqdm(range(0, n_rows, batch_size), desc="Identifying Names"):
        end_idx = min(start_idx + batch_size, n_rows)
        
        # Get the current batch of text
        batch_texts = df[text_column][start_idx:end_idx].to_list()
        
        # Clean and filter candidates for this batch
        candidates_to_process = []
        original_indices = []  # Maps candidate index back to original row index
        
        for i, text in enumerate(batch_texts):
            if text is None:
                continue
                
            cleaned_text = clean_element(text)
            if is_likely_name_candidate(cleaned_text):
                candidates_to_process.append(cleaned_text)
                original_indices.append(start_idx + i)  # Store the absolute row index
        
        # Skip if no candidates in this batch
        if not candidates_to_process:
            continue
            
        try:
            # Process all candidates with NER
            ner_results = ner(candidates_to_process)
            
            # Mark positive results
            for i, result_list in enumerate(ner_results):
                for entity in result_list:
                    if entity["entity_group"] == "PER" and entity["score"] > 0.8:
                        # Get the original row index and mark as True
                        original_row_idx = original_indices[i]
                        is_name_results[original_row_idx] = True
                        break  # Found a name, move to next candidate
                        
        except Exception as e:
            print(f"Error processing batch starting at {start_idx}: {e}")
            continue
    
    print("Name identification complete.")
    
    # Add the boolean column to the DataFrame
    return df.with_columns(
        pl.Series(name=target_column, values=is_name_results)
    )


def extract_names_column_batch(df: pl.DataFrame, source_column: str, target_column: str, batch_size: int = 500) -> pl.DataFrame:
    """
    Extracts names by processing the DataFrame in batches of rows.
    This is memory-efficient and leverages batch processing in the NER model.
    """
    ner = get_ner_model()
    n_rows = len(df)
    all_extracted_names = []

    print(f"Processing {n_rows} rows in batches of {batch_size}...")

    for start_idx in tqdm(range(0, n_rows, batch_size), desc="Extracting Names"):
        end_idx = min(start_idx + batch_size, n_rows)
        
        # 1. Get the current batch of rows from the Polars Series
        rows_batch = df[source_column][start_idx:end_idx]
        
        # 2. Collect all valid candidates from this batch of rows
        batch_candidates = []
        # This list maps each candidate back to its row index *within the current batch*
        candidate_to_batch_row_idx = []

        for i, string_list in enumerate(rows_batch):
            if not string_list:
                continue
            for element in string_list:
                cleaned = clean_element(element)
                if is_likely_name_candidate(cleaned):
                    batch_candidates.append(cleaned)
                    candidate_to_batch_row_idx.append(i)
        
        # 3. Process all candidates from this batch with the NER model
        if not batch_candidates:
            # If no candidates in this batch, append empty lists for each row
            all_extracted_names.extend([[] for _ in range(len(rows_batch))])
            continue

        try:
            ner_results = ner(batch_candidates)
        except Exception as e:
            print(f"An error occurred during NER processing in a batch: {e}")
            # On error, append empty lists to avoid crashing
            all_extracted_names.extend([[] for _ in range(len(rows_batch))])
            continue

        # 4. Map the results back to their original rows within the batch
        batch_row_names = [[] for _ in range(len(rows_batch))]
        for i, result_list in enumerate(ner_results):
            # Check if any entity in the result is a person
            for entity in result_list:
                if entity["entity_group"] == "PER" and entity["score"] > 0.85:
                    # Get the original row index for this candidate
                    original_batch_row_idx = candidate_to_batch_row_idx[i]
                    # Append the original, cleaned text
                    batch_row_names[original_batch_row_idx].append(batch_candidates[i])
                    break # Found a name, move to the next candidate
        
        # Remove duplicates within each row's list of names
        unique_batch_names = [list(set(names)) for names in batch_row_names]
        all_extracted_names.extend(unique_batch_names)

    print("Name extraction complete.")
    # 5. Add the final list of lists as a new column to the DataFrame
    return df.with_columns(
        pl.Series(name=target_column, values=all_extracted_names)
    )

# We can simplify the main entry point now
def test_long_format_extraction():
    """Test the name extraction with long format data"""
    
    # Create sample wide data
    wide_df = pl.DataFrame({
        "page_id": ["page_1", "page_2", "page_3"],
        "Table Contents": [
            ["Cross, Anton Nelson", "| 02/04/1999", "Murder 1*, Agg Battery", "Smith, John"],
            ["Johnson, Mary Jane", "Gannon Andres", "This is not a name", "SHERIFF DEPT"],
            ['Camacho, Juan L1S1218','4/01/1995.','01/03/2021']
        ]
    })
    
    print("--- Original Wide DataFrame ---")
    print(wide_df)
    
    # Reshape to long format
    long_df = reshape_to_long(wide_df, id_cols="page_id", list_col="Table Contents")
    
    print("\n--- Long DataFrame ---")
    print(long_df)
    
    # Identify names
    result_df = identify_names_in_long_df(
        long_df, 
        text_column="Table Contents", 
        target_column="is_name",
        batch_size=5  # Small batch for testing
    )
    
    print("\n--- Result with Name Identification ---")
    print(result_df)
    
    # Show just the names
    names_only = result_df.filter(pl.col("is_name"))
    print("\n--- Identified Names Only ---")
    print(names_only)
    
    return result_df

if __name__ == "__main__":
    test_long_format_extraction()

#example = ['Odio, Chevaz' '- 07227120 17' 'Aggravated Arson' '12/ 10/ 1988'
# '"Calvin, Maria' '04/07/1985' 'Man / Del Controlled Substance'
# 'if 1/03/2018 | 8']

# start the batchsize as ram can fit and increase a speed is increasing. 