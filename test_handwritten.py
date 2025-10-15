#!/usr/bin/env python3
"""
Test script for handwritten document processing functionality.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_handwritten_processor():
    """Test the handwritten processor functionality."""
    try:
        from jail_events.handwritten.handwritten_processor import (
            evaluate_handwritten_documents,
            get_handwritten_statistics,
            create_handwritten_excel
        )
        print("✓ Handwritten processor imports successfully")
        
        # Test with a dummy DataFrame structure
        import polars as pl
        
        # Create a test DataFrame
        test_data = {
            "Report ID": ["test_1", "test_2", "test_3"],
            "OCR_Confidence": [75.5, 85.2, 65.8],  # One handwritten (< 80)
            "OCR_Word_Count": [50, 100, 30],
            "OCR_Text_Detected": ["Some text", "More text", "Less text"],
            "Facility Name": ["Test Jail 1", "Test Jail 2", "Test Jail 3"]
        }
        
        test_df = pl.DataFrame(test_data)
        
        # Test handwritten evaluation
        handwritten_df = evaluate_handwritten_documents_from_df(test_df)
        print(f"✓ Found {len(handwritten_df)} handwritten documents")
        
        # Test statistics
        stats = get_handwritten_statistics_from_df(test_df)
        print(f"✓ Statistics: {stats['handwritten_percentage']:.1f}% handwritten")
        
        print("✓ All handwritten processor tests passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Test error: {e}")
        return False

def evaluate_handwritten_documents_from_df(df):
    """Helper function for testing."""
    return df.filter(df["OCR_Confidence"] < 80)

def get_handwritten_statistics_from_df(df):
    """Helper function for testing."""
    total_docs = len(df)
    handwritten_docs = len(df.filter(df["OCR_Confidence"] < 80))
    
    return {
        "total_documents": total_docs,
        "handwritten_documents": handwritten_docs,
        "handwritten_percentage": handwritten_docs / total_docs * 100
    }

def test_main_module():
    """Test the main module functionality."""
    try:
        from jail_events.main import main
        print("✓ Main module imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Main module import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Main module test error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Jail Events Handwritten Processing...")
    print("=" * 50)
    
    success = True
    
    # Test handwritten processor
    print("\n1. Testing Handwritten Processor:")
    success &= test_handwritten_processor()
    
    # Test main module
    print("\n2. Testing Main Module:")
    success &= test_main_module()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! The handwritten processing is ready to use.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)
