import polars as pl
import re
from transformers import pipeline
import torch.cuda
ner_model = None

def get_ner_model():
    """Initialization of NER model"""
    global ner_model
    if ner_model is None:
        ner_model = pipeline("ner", 
                          model="dbmdz/bert-large-cased-finetuned-conll03-english", 
                          aggregation_strategy="simple")
        # ner_model = pipeline("ner", 
        #                    model="distilbert-base-cased",  # 268MB vs 1.33GB
        #                    aggregation_strategy="simple",
        #                    device=0 if torch.cuda.is_available() else -1)  # Use GPU if available
    return ner_model

# Function for extracting names from the polars columns 
def clean_element(element):
    """ Clean a str element"""
    # Remove OCR artifacts and numbers
    cleaned = re.sub(r'[|\\/\n\t\r"]+', ' ', element)  # Remove OCR artifacts
    cleaned = re.sub(r'\d+', '', cleaned)  # Remove numbers
    cleaned = re.sub(r'[^\w\s,\'-]', '', cleaned)  # Keep only letters, spaces, commas, apostrophes, hyphens
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Clean multiple spaces
    
    return cleaned


def is_likely_name(text = ""):
    """
    Using bert NLP free model, is that str a name? 
    """
    
    if not text or len(text)<3:
        return False
    
    exclusions = ['murder', 'battery', 'assault', 'theft', 'warrant', 'arson', 
                 'substance', 'controlled', 'aggravated', 'felony', 'misdemeanor']
    
    if any(word in text.lower() for word in exclusions):
        return False
    
    words = text.split()
    if len(words) > 5:  # Too many words, probably not a name
        return False
        
    return True
    

def check_with_ner(text):
    """ Check text is a name using NER model"""
    ner = get_ner_model()
    entities = ner(text)
    
    for entity in entities:
        if entity["entity_group"] == "PER" and entity["score"] > 0.8:
            return True
    return False

def extract_names_from_list(string_list):
    """Extract names from a list of strings - main function"""
    if not string_list:
        return []
    
    names = []
    
    for element in string_list:
        # Skip dates (contain '/')
        if '/' in element:
            continue
            
        # Clean the element
        cleaned = clean_element(element)
        
        # Quick filter
        if not is_likely_name(cleaned):
            continue
            
        # Final check with NER
        if check_with_ner(cleaned):
            names.append(cleaned)

    # Remove duplicates
    return list(set(names))  


def extract_names_column(df, source_column='Table Contents', 
                         target_column='Extracted_Names', use_batch = True):
    """
    Extract names from a Polars DataFrame column containing lists of strings
    
    Args:
        df: Polars DataFrame
        source_column: Column name containing list of strings
        target_column: New column name for extracted names
    
    Returns:
        DataFrame with new column containing extracted names
    """
    
    if use_batch:
        return extract_names_column_batch(df, source_column, target_column)
    else:
        return df.with_columns(
            pl.col(source_column)
            .map_elements(extract_names_from_list, return_dtype=pl.List(pl.String))
            .alias(target_column)
        )
    
def extract_names_column_batch(df, source_column='Table Contents', target_column='Extracted_Names'):
    """
    Extract names using full column batching for maximum efficiency
    Handles multiple names per row correctly
    
    Args:
        df: Polars DataFrame
        source_column: Column name containing list of strings
        target_column: New column name for extracted names
    
    Returns:
        DataFrame with new column containing extracted names
    """
    
    # Step 1: Collect ALL candidates from ALL rows with row tracking
    all_candidates = []
    candidate_to_row = []  # Maps each candidate back to its row index
    candidate_to_original = []  # Maps each candidate back to its original text
    
    for row_idx in range(len(df)):
        string_list = df[source_column][row_idx]
        
        if not string_list:
            continue
            
        for element in string_list:
            # Skip dates (contain '/')
            if '/' in element:
                continue
                
            # Clean the element
            cleaned = clean_element(element)
            
            # Quick filter
            if not is_likely_name(cleaned):
                continue
                
            # Store candidate with row mapping
            all_candidates.append(cleaned)
            candidate_to_row.append(row_idx)
            candidate_to_original.append(cleaned)
    
    print(f"Processing {len(all_candidates)} candidates in batch...")
    
    # Step 2: Process ALL candidates in ONE batch call
    if not all_candidates:
        # No candidates found, return empty list for all rows
        empty_lists = [[] for _ in range(len(df))]
        return df.with_columns(
            pl.Series(name=target_column, values=empty_lists)
        )
    
    # Batch NER processing
    ner = get_ner_model()
    try:
        # Split into smaller batches if too large (avoid memory issues)
        batch_size = 100  # Adjust based on your memory
        all_results = []
        
        for i in range(0, len(all_candidates), batch_size):
            batch = all_candidates[i:i + batch_size]
            batch_results = ner(batch)
            all_results.extend(batch_results)
        
        print(f"Batch processing complete. Processing {len(all_results)} results...")
        
    except Exception as e:
        print(f"Batch NER failed: {e}. Falling back to individual processing...")
        # Fallback to original method if batch fails
        return extract_names_column(df, source_column, target_column)
    
    # Step 3: Map results back to rows (handling multiple names per row)
    row_names = [[] for _ in range(len(df))]  # Initialize empty list for each row
    
    for i, result in enumerate(all_results):
        row_idx = candidate_to_row[i]
        original_text = candidate_to_original[i]
        
        # Check if this candidate is a name
        is_name = False
        for entity in result:
            if entity["entity_group"] == "PER" and entity["score"] > 0.8:
                is_name = True
                break
        
        if is_name:
            row_names[row_idx].append(original_text)
    
    # Step 4: Remove duplicates within each row
    row_names = [list(set(names)) for names in row_names]
    
    print(f"Extraction complete. Found names in {sum(1 for names in row_names if names)} rows.")
    
    return df.with_columns(
        pl.Series(name=target_column, values=row_names)
    )

 
# Test function
def test_extraction():
    """Test the name extraction with sample data"""
    sample_data = [
        "Cross, Anton Nelson",
        "| 02/04/1999", 
        "Murder 1*, Agg Battery",
        "Smith, John",
        "- 07227120 17",
        "Johnson, Mary Jane", 
        "Gannon Andres"
    ]
    
    result = extract_names_from_list(sample_data)
    print("Extracted names:", result)
    return result

if __name__ == "__main__":
    test_extraction()

#example = ['Odio, Chevaz' '- 07227120 17' 'Aggravated Arson' '12/ 10/ 1988'
# '"Calvin, Maria' '04/07/1985' 'Man / Del Controlled Substance'
# 'if 1/03/2018 | 8']

# start the batchsize as ram can fit and increase a speed is increasing. 