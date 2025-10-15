"""
Address cleaning and normalization utilities for jail addresses.
"""

import re
import polars as pl
from typing import List, Tuple, Optional
import jellyfish

def clean_address(address: str) -> str:
    """
    Clean and normalize an address string.
    
    Args:
        address: Raw address string
        
    Returns:
        Cleaned address string
    """
    if not address or address.strip() == "":
        return ""
    
    # Convert to uppercase for consistency
    cleaned = address.upper().strip()
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Common abbreviations and standardizations
    replacements = {
        r'\bSTREET\b': 'ST',
        r'\bAVENUE\b': 'AVE',
        r'\bBOULEVARD\b': 'BLVD',
        r'\bROAD\b': 'RD',
        r'\bDRIVE\b': 'DR',
        r'\bCOURT\b': 'CT',
        r'\bPLACE\b': 'PL',
        r'\bLANE\b': 'LN',
        r'\bNORTH\b': 'N',
        r'\bSOUTH\b': 'S',
        r'\bEAST\b': 'E',
        r'\bWEST\b': 'W',
        r'\bSOUTHEAST\b': 'SE',
        r'\bSOUTHWEST\b': 'SW',
        r'\bNORTHEAST\b': 'NE',
        r'\bNORTHWEST\b': 'NW',
        r'\bILLINOIS\b': 'IL',
        r'\bCHICAGO\b': 'CHICAGO',
        r'\bCICERO\b': 'CICERO',
        r'\bLYONS\b': 'LYONS',
        r'\bDIVISION\b': 'DIV',
        r'\bDEPT\b': 'DEPT',
        r'\bDEPARTMENT\b': 'DEPT',
        r'\bCORRECTIONS\b': 'CORR',
        r'\bJAIL\b': 'JAIL',
        r'\bFACILITY\b': 'FAC',
        r'\bCENTER\b': 'CTR',
        r'\bDETENTION\b': 'DET',
        r'\bTEMPORARY\b': 'TEMP',
        r'\bJUVENILE\b': 'JUV',
        r'\bPOLICE\b': 'PD',
        r'\bCOUNTY\b': 'CO',
        r'\bCOOK\b': 'COOK',
    }
    
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned)
    
    # Remove common prefixes/suffixes that don't help with matching
    cleaned = re.sub(r'^(THE\s+|A\s+)', '', cleaned)
    cleaned = re.sub(r'\s+(INC|LLC|CORP|LTD)\.?$', '', cleaned)
    
    # Remove punctuation except for periods in abbreviations and commas
    cleaned = re.sub(r'[^\w\s\.,]', ' ', cleaned)
    
    # Clean up multiple spaces again
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def extract_key_components(address: str) -> Tuple[str, str, str, str]:
    """
    Extract key components from an address.
    
    Args:
        address: Address string
        
    Returns:
        Tuple of (street_number, street_name, city, zip_code)
    """
    cleaned = clean_address(address)
    
    # Extract zip code (5 digits at the end)
    zip_match = re.search(r'\b(\d{5})\b', cleaned)
    zip_code = zip_match.group(1) if zip_match else ""
    
    # Remove zip code from address
    address_no_zip = re.sub(r'\b\d{5}\b', '', cleaned).strip()
    
    # Extract street number (digits at the beginning)
    street_match = re.match(r'^(\d+)', address_no_zip)
    street_number = street_match.group(1) if street_match else ""
    
    # Extract street name (everything after street number)
    street_name = re.sub(r'^\d+\s*', '', address_no_zip).strip()
    
    # Try to extract city (common Cook County cities)
    cities = ['CHICAGO', 'CICERO', 'LYONS', 'EVANSTON', 'OAK PARK', 'BERWYN']
    city = ""
    for c in cities:
        if c in cleaned:
            city = c
            break
    
    return street_number, street_name, city, zip_code

def calculate_address_similarity(addr1: str, addr2: str) -> float:
    """
    Calculate similarity between two addresses using multiple methods.
    
    Args:
        addr1: First address
        addr2: Second address
        
    Returns:
        Similarity score between 0 and 1
    """
    if not addr1 or not addr2:
        return 0.0
    
    # Clean both addresses
    clean1 = clean_address(addr1)
    clean2 = clean_address(addr2)
    
    if clean1 == clean2:
        return 1.0
    
    # Use Jaro-Winkler distance (good for addresses)
    jaro_winkler = jellyfish.jaro_winkler_similarity(clean1, clean2)
    
    # Use Levenshtein distance
    levenshtein = 1 - (jellyfish.levenshtein_distance(clean1, clean2) / max(len(clean1), len(clean2)))
    
    # Use Jaro distance
    jaro = jellyfish.jaro_similarity(clean1, clean2)
    
    # Weighted average (Jaro-Winkler is best for addresses)
    similarity = (jaro_winkler * 0.5) + (levenshtein * 0.3) + (jaro * 0.2)
    
    return similarity

def find_best_address_match(target_address: str, candidate_addresses: List[str], threshold: float = 0.7) -> Optional[Tuple[str, float]]:
    """
    Find the best matching address from a list of candidates.
    
    Args:
        target_address: Address to match
        candidate_addresses: List of candidate addresses
        threshold: Minimum similarity threshold
        
    Returns:
        Tuple of (best_match, similarity_score) or None if no good match
    """
    if not target_address or not candidate_addresses:
        return None
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidate_addresses:
        score = calculate_address_similarity(target_address, candidate)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
    
    return (best_match, best_score) if best_match else None

def cluster_similar_addresses(addresses: List[str], threshold: float = 0.8) -> List[List[str]]:
    """
    Cluster addresses by similarity.
    
    Args:
        addresses: List of addresses to cluster
        threshold: Similarity threshold for clustering
        
    Returns:
        List of clusters, where each cluster is a list of similar addresses
    """
    if not addresses:
        return []
    
    clusters = []
    used_indices = set()
    
    for i, addr1 in enumerate(addresses):
        if i in used_indices:
            continue
            
        cluster = [addr1]
        used_indices.add(i)
        
        for j, addr2 in enumerate(addresses[i+1:], i+1):
            if j in used_indices:
                continue
                
            if calculate_address_similarity(addr1, addr2) >= threshold:
                cluster.append(addr2)
                used_indices.add(j)
        
        clusters.append(cluster)
    
    return clusters
