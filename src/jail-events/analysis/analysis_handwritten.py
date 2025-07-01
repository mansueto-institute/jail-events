import numpy as np
import pytesseract
from typing import Dict, List
from pathlib import Path
import polars as pl
import altair as alt
import pandas as pd

def extract_ocr_confidence(cleanned_image) -> Dict:
    """
    Get the confidence from the OCR process
    """
    tesseract_config = "--oem 3 --psm 3 -l eng"
    ocr_data = pytesseract.image_to_data(
        cleanned_image, 
        output_type = pytesseract.Output.DICT,
        config = tesseract_config, 
        timeout = 15
    )
    
    # Confidence scores valid
    confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) >0]
    
    if confidences:
        return {
            'avg_confidence': np.mean(confidences),
            'word_count': len(confidences),
            'text_detected': True
        }
    return{
        'avg_confidence': 0.0,
        'word_count': 0,
        'text_detected': False
    }


# Analysis
def generate_handwritten_report(data_list: List[Dict],
                                output: Path, 
                                threshold: float=60.0):
    """
    Report about handtwrittern results
    """

    df = pl.DataFrame(data_list)
    text_df = df.filter(pl.col('OCR_Text_Detected') == True)
    
    if text_df.height == 0:
        print("No text detected")
        return
    
    stats = text_df.select([
        pl.col('OCR_Confidence').mean().alias('mean_confidence'),
        pl.col('OCR_Confidence').median().alias('median_confidence'),
        pl.col('OCR_Confidence').std().alias('std_confidence'),
        pl.col('OCR_Confidence').min().alias('min_confidence'),
        pl.col('OCR_Confidence').max().alias('max_confidence'),
    ]).row(0, named=True)
    
    classified_df = text_df.with_columns([
        pl.when(pl.col('OCR_Confidence') >= threshold)
        .then(pl.lit('typed'))
        .otherwise(pl.lit('handwritten'))
        .alias('page_type')
    ])
    
    # count by type
    type_counts = classified_df.group_by(
        'page_type').agg(pl.len().alias('count'))
    
    for row in type_counts.iter_rows(named=True):
        percentage = row['count'] / text_df.height * 100
        print(f"  {row['page_type'].title()}: {row['count']} pages ({percentage:.1f}%)")
    
    # Summary
    print(f"Total pages with text: {text_df.height}")
    print(f"Mean confidence: {stats['mean_confidence']:.1f}")
    print(f"Median confidence: {stats['median_confidence']:.1f}")
    print(f"Range: {stats['min_confidence']:.1f} - {stats['max_confidence']:.1f}")
    
    # Create histogram
    histogram = alt.Chart(classified_df).mark_bar(
        opacity=0.7,
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X(
            'OCR_Confidence:Q',
            bin=alt.Bin(maxbins=20, extent=[0, 100]),
            title='OCR Confidence Score'
        ),
        y=alt.Y('count():Q', title='Number of Pages'),
        color=alt.Color(
            'page_type:N',
            scale=alt.Scale(
                domain=['typed', 'handwritten'],
                range=["#81aa81", "#d28bd3"]
            ),
            title='Page Type'
        ),
        tooltip=[
            alt.Tooltip('count():Q', title='Pages'),
            alt.Tooltip('OCR_Confidence:Q', bin=True, title='Confidence Range'),
            'page_type:N'
        ]
    )
    
    # Add threshold line
    threshold_line = alt.Chart(pl.DataFrame({'threshold':[threshold]})).mark_rule(
    color='red', strokeDash=[5, 5], size=2).encode(x='threshold:Q')
    
    # Combine chart
    chart = (histogram + threshold_line).properties(
        width=600,
        height=400,
        title=f'OCR Confidence Distribution (Threshold = {threshold})'
    )
    
    # Save chart
    chart_path = output / "confidence_histogram.html"
    chart.save(str(chart_path))
    print(f"Histogram saved to: {chart_path}")
