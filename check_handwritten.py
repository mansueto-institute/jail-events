#!/usr/bin/env python3
"""
Simple test to check what handwritten pages might be missing from person records.
"""

import polars as pl
from pathlib import Path

def check_missing_handwritten():
    """Check which handwritten pages are missing from person records."""
    
    output_dir = Path("src/jail-events/data/jails-data/output")
    person_records = output_dir / "jails_person_records.parquet"
    raw_data = output_dir / "jails_pdfs_full.parquet"
    
    if not person_records.exists():
        print("❌ Person records not found!")
        return
    
    if not raw_data.exists():
        print("❌ Raw data not found!")
        return
    
    print("📊 Analyzing handwritten pages...")
    
    # Read person records
    person_df = pl.read_parquet(person_records)
    processed_pages = set(person_df["Report ID"].unique())
    print(f"✓ Person records contain {len(processed_pages)} processed pages")
    
    # Read raw data
    raw_df = pl.read_parquet(raw_data)
    all_pages = set(raw_df["Report ID"].unique())
    print(f"✓ Raw data contains {len(all_pages)} total pages")
    
    # Find handwritten pages (OCR < 80)
    handwritten_pages = set(
        raw_df.filter(pl.col("OCR_Confidence") < 80)["Report ID"].unique()
    )
    print(f"✓ Found {len(handwritten_pages)} handwritten pages (OCR < 80)")
    
    # Find missing handwritten pages
    missing_handwritten = handwritten_pages - processed_pages
    print(f"✓ Missing handwritten pages: {len(missing_handwritten)}")
    
    if len(missing_handwritten) > 0:
        print(f"📝 Missing handwritten pages:")
        for page in sorted(list(missing_handwritten))[:10]:  # Show first 10
            print(f"   - {page}")
        if len(missing_handwritten) > 10:
            print(f"   ... and {len(missing_handwritten) - 10} more")
        
        print(f"\n🎯 Recommendation: Run handwritten processing for {len(missing_handwritten)} missing pages")
        print("   Command: make handwritten-smart")
    else:
        print("✅ All handwritten pages already processed!")
    
    # Show OCR confidence distribution
    print(f"\n📈 OCR Confidence Distribution:")
    ocr_stats = raw_df.select([
        pl.col("OCR_Confidence").min().alias("min"),
        pl.col("OCR_Confidence").max().alias("max"),
        pl.col("OCR_Confidence").mean().alias("avg"),
        pl.col("OCR_Confidence").median().alias("median")
    ]).to_dicts()[0]
    
    print(f"   Min: {ocr_stats['min']:.1f}")
    print(f"   Max: {ocr_stats['max']:.1f}")
    print(f"   Avg: {ocr_stats['avg']:.1f}")
    print(f"   Median: {ocr_stats['median']:.1f}")

if __name__ == "__main__":
    print("Handwritten Pages Analysis")
    print("=" * 40)
    check_missing_handwritten()
