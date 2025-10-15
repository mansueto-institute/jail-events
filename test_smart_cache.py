#!/usr/bin/env python3
"""
Test script to verify the smart cache checking for handwritten processing.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cache_status():
    """Test the cache status checking functionality."""
    try:
        from jail_events.handwritten.handwritten_processor import check_handwritten_cache_status
        print("✓ Cache status function imports successfully")
        
        # Test with the actual output directory
        output_dir = Path("src/jail-events/data/jails-data/output")
        
        if output_dir.exists():
            status = check_handwritten_cache_status(output_dir)
            print(f"✓ Cache status check completed")
            print(f"  - Person records exist: {status['person_records_exists']}")
            print(f"  - Raw data exists: {status['raw_data_exists']}")
            print(f"  - Handwritten parquet exists: {status['handwritten_parquet_exists']}")
            print(f"  - Handwritten excel exists: {status['handwritten_excel_exists']}")
            print(f"  - Handwritten pages missing: {status['handwritten_pages_missing']}")
            if 'missing_count' in status:
                print(f"  - Missing count: {status['missing_count']}")
            if 'total_handwritten' in status:
                print(f"  - Total handwritten: {status['total_handwritten']}")
            print(f"  - Needs full pipeline: {status['needs_full_pipeline']}")
            print(f"  - Reason: {status['reason']}")
            
            return True
        else:
            print(f"❌ Output directory not found: {output_dir}")
            return False
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Test error: {e}")
        return False

def test_file_existence():
    """Test which files actually exist."""
    print("\nChecking file existence...")
    
    output_dir = Path("src/jail-events/data/jails-data/output")
    handwritten_dir = Path("src/jail-events/data/jails-data/handwritten_party")
    
    files_to_check = [
        ("Raw data", output_dir / "jails_pdfs_full.parquet"),
        ("Person records", output_dir / "jails_person_records.parquet"),
        ("Cleaned data", output_dir / "jails_pdfs_cleaned.parquet"),
        ("Handwritten parquet", handwritten_dir / "handwritten_cleaned.parquet"),
        ("Handwritten excel", handwritten_dir / "handwritten_documents.xlsx"),
    ]
    
    all_exist = True
    for name, path in files_to_check:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"✓ {name}: {path} ({size_mb:.1f} MB)")
        else:
            print(f"❌ {name}: {path}")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("Testing Smart Cache Checking for Handwritten Processing...")
    print("=" * 60)
    
    success = True
    
    # Test file existence
    print("\n1. Checking file existence:")
    success &= test_file_existence()
    
    # Test cache status
    print("\n2. Testing cache status logic:")
    success &= test_cache_status()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed! Smart cache checking is working.")
        print("\nRecommended workflow:")
        print("  1. make handwritten-smart    # Checks cache and processes if needed")
        print("  2. If cache is outdated, run: make full-pipeline")
        print("  3. Then run: make handwritten-smart")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)
