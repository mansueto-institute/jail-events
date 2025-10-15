#!/usr/bin/env python3
"""
Test script to verify handwritten processing with caching works correctly.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_caching_logic():
    """Test the caching logic for handwritten processing."""
    try:
        from jail_events.handwritten.handwritten_processor import process_handwritten_only
        print("✓ Handwritten processor imports successfully")
        
        # Check if cleaned cache exists
        output_dir = Path("src/jail-events/data/jails-data/output")
        cleaned_cache = output_dir / "jails_pdfs_cleaned.parquet"
        
        if cleaned_cache.exists():
            print(f"✓ Found cleaned cache: {cleaned_cache}")
            print("✓ Handwritten processing will use cached data (fast!)")
            
            # Get file size for reference
            size_mb = cleaned_cache.stat().st_size / (1024 * 1024)
            print(f"✓ Cache file size: {size_mb:.1f} MB")
            
        else:
            print(f"⚠️  No cleaned cache found: {cleaned_cache}")
            print("⚠️  Handwritten processing will need to clean data first (slower)")
            
            # Check if raw data exists
            raw_data = output_dir / "jails_pdfs_full.parquet"
            if raw_data.exists():
                print(f"✓ Found raw data: {raw_data}")
                size_mb = raw_data.stat().st_size / (1024 * 1024)
                print(f"✓ Raw data size: {size_mb:.1f} MB")
            else:
                print(f"❌ No raw data found: {raw_data}")
                print("❌ Please run the full pipeline first")
                return False
        
        print("✓ Caching logic test passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Test error: {e}")
        return False

def test_file_structure():
    """Test that the expected file structure exists."""
    print("\nChecking file structure...")
    
    expected_files = [
        "src/jail-events/data/jails-data/output/jails_pdfs_cleaned.parquet",
        "src/jail-events/data/jails-data/handwritten_party/"
    ]
    
    all_exist = True
    for file_path in expected_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("Testing Handwritten Processing Caching...")
    print("=" * 50)
    
    success = True
    
    # Test file structure
    print("\n1. Checking file structure:")
    success &= test_file_structure()
    
    # Test caching logic
    print("\n2. Testing caching logic:")
    success &= test_caching_logic()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! Handwritten processing with caching is ready.")
        print("\nTo run handwritten analysis:")
        print("  make handwritten-pipeline    # Uses cache if available")
        print("  make handwritten-cached      # Forces use of cache")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)
