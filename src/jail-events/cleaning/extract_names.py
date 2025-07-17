import polars as pl
import re
from transformers import pipeline

ner_model = None

def get_ner_model():
    """Lazy initialization of NER model"""
    global ner_model
    if ner_model is None:
        ner_model = pipeline("ner", 
                           model="dbmdz/bert-large-cased-finetuned-conll03-english", 
                           aggregation_strategy="simple")
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


def extract_names_column(df, source_column='Table Contents', target_column='Extracted_Names'):
    """
    Extract names from a Polars DataFrame column containing lists of strings
    
    Args:
        df: Polars DataFrame
        source_column: Column name containing list of strings
        target_column: New column name for extracted names
    
    Returns:
        DataFrame with new column containing extracted names
    """
    return df.with_columns(
        pl.col(source_column)
        .map_elements(extract_names_from_list, return_dtype=pl.List(pl.String))
        .alias(target_column)
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