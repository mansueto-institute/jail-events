from pathlib import Path
import pickle
from pdf_processing.page_functions import scrape_page
from tqdm import tqdm
import fitz, cv2
from preprocess.cleaning import pre_process_page
from concurrent.futures import ProcessPoolExecutor, as_completed
import polars as pl
from analysis.analysis_handwritten import extract_ocr_confidence
from xlsxwriter import Workbook
import random

def parse_image_dict(cleaned_img, key_id, image_path, origin_page, dpi, title_key):
    """
    Parse a cleanded image into a dictionaries to json
    """
    cleaned_rep_dict = scrape_page(cleaned_img)
    # If return the no year found, del and process again
    if cleaned_rep_dict == "No year found":
        #delete image file
        image_path.unlink(missing_ok = True)
        img = pre_process_page(page = origin_page, reprocess= True)
        cv2.imwrite(str(image_path), img)
        cleaned_rep_dict = scrape_page(img)
        cleaned_rep_dict["process"] = "reprocess"

    else: 
        cleaned_rep_dict["process"] = "normal"
        
    cleaned_rep_dict["Report ID"] = key_id
    
    # Remove the problematic nested dictionary field
    if "Occurrence Dictionary" in cleaned_rep_dict:
        del cleaned_rep_dict["Occurrence Dictionary"]
    
    # Adding OCR analysis 
    if cleaned_rep_dict.get("process") == "reprocess":
        # For reprocessed images, analyze the new image
        confidence_data = extract_ocr_confidence(img)
    else:
        # For normal processing, use the original cleaned_img
        confidence_data = extract_ocr_confidence(cleaned_img)
    cleaned_rep_dict.update({
        "OCR_Confidence": confidence_data['avg_confidence'],
        "OCR_Word_Count": confidence_data['word_count'],
        "OCR_Text_Detected": confidence_data['text_detected']
    })

    return cleaned_rep_dict

def process_single_pdf(pdf_path: Path, out_dir: Path, dpi: int=300,
                       title_key: str = "REPORT EXTRAORDINARY UNUSUAL"):
    """
    Process of all the pages in a single pdf and return list dictionaries
    """
    doc = fitz.open(pdf_path)
    pdf_stem = pdf_path.stem
    list_dicts = []
    processing_log = []
    for i, page in enumerate(doc):
        page_id = f"{pdf_stem}_p{i+1}"
        log_entry = {
            "pdf_name": pdf_stem,
            "page_number": i+1,
            "page_id": page_id,
            "status": "unknown",
            "error_stage": "",
            "error_message": ""
        }
        try:
            if page_id == 'UO - FOIA June 2020 p116_p1':
                print(page_id)
            img = pre_process_page(page, dpi=dpi,
                                title_keyword=title_key)
            if img is None:
                log_entry.update({
                    "status": "failed",
                    "error_stage": "preprocessing",
                    "error_message": "Image preprocessing returned None"
                })
                processing_log.append(log_entry)
                continue
            image_path = out_dir / f"{page_id}.png"
            cv2.imwrite(str(image_path), img)
    
            try:
                page_dict = parse_image_dict(img, page_id, image_path, page,
                                             dpi, title_key)
                list_dicts.append(page_dict)
                log_entry.update({
                    "status": "success",
                    "error_stage": "",
                    "error_message": ""
                })
                processing_log.append(log_entry)
            except Exception as e:
                log_entry.update({
                    "status": "failed",
                    "error_stage": "parse_image_dict",
                    "error_message": f"OCR/parsing error: {str(e)}"
                })
                processing_log.append(log_entry)
                continue
        except Exception as e:
            log_entry.update({
                "status": "failed",
                "error_stage": "general",
                "error_message": f"Unexpected error: {str(e)}"
            })
            processing_log.append(log_entry)
            print(f"Error processing page {i+1} in {pdf_stem}: {e}")
            continue
    doc.close()
    return list_dicts, processing_log
        

def process_all_pdfs(src_folder: Path, dst_folder: Path, dpi: int = 300):
    """
    Process all PDFS in Folder and return a list of dicts
    """
    dst_folder.mkdir(parents=True, exist_ok=True)
    pdf_files = list(src_folder.glob("*.pdf"))
    random.shuffle(pdf_files)
    if not pdf_files:
        print(f"No PDF files in folder")
        return [], []
    
    list_docs = []
    all_processing_logs = []
    
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_single_pdf,
                                   pdf,
                                   dst_folder,
                                   dpi): pdf for pdf in pdf_files}
        for future in tqdm(as_completed(futures), total=len(pdf_files),
                           desc="Processing PDFs"):
            try:
                result_dicts, processing_log  = future.result()
                list_docs.extend(result_dicts)
                all_processing_logs.extend(processing_log)
            except Exception as e:
                pdf_path = futures[future]
                print(f"Error processing {pdf_path.name}: {e}")
                #PDF - level error
                all_processing_logs.append({
                    "pdf_name": pdf_path.stem,
                    "page_number": 0,
                    "page_id": f"{pdf_path.stem}_PDF_LEVEL_ERROR",
                    "status": "failed",
                    "error_stage": "pdf_level",
                    "error_message": f"PDF-level error: {str(e)}"
                })
    
    return list_docs, all_processing_logs

def add_hyperlink_column(df, base_url):
    """
    Helper function fo add hyperlink column to any df with REPORT ID
    This works for OneDrive links, not Box
    """
    return df.with_columns([
        (pl.lit('=HYPERLINK("') + 
         pl.lit(base_url) + 
         pl.col("Report ID").str.replace(" ", "%20") + 
         pl.lit('.png?Web=1", "View Image")')
        ).alias("Image_Link")
    ])


def export_parquets_excel(in_parquet_pages, in_parquet_persons,
                          excel_file , base_url):
    """Export the final parquet to Excel with hyperlinks to images """
    
    # Read the parquet file
    df_pages = pl.read_parquet(in_parquet_pages)
    df_persons = pl.read_parquet(in_parquet_persons)
    df_pages = df_pages.select(["Report ID", "Cleaned Facility Name", "Cleaned Address", "Zip Code", "Cleaned Date",
                                            "Cleaned Time of Day", "Cleaned Occurrences", "Injuries?", "Resulting Death?", "Deceased Name",
                                            "Deceased Cause", "Deceased Date and Time", "Deceased on Suicide Watch", "Deceased Reporter", "Deceased Examined by Physician",
                                            "OCR_Confidence", "OCR_Word_Count", "Facility Name", "RD Number", "Phone Number", "Address", "Date",
                                            "Time of Day", "AM or PM", "Occurrence", "Table Contents"])
    
    # Create hyperlink column
    df_pages = add_hyperlink_column(df_pages, base_url)
    df_persons = add_hyperlink_column(df_persons, base_url)

    with Workbook(excel_file) as wb:
        #formats
        hyperlink_format = wb.add_format({
            'font_color': "#7070E3",
            'underline': True
        })
        
        #wirte pages dataset to first sheet
        df_pages.write_excel(
            workbook=wb, 
            worksheet='Pages database',
            column_formats={"Image_Link": hyperlink_format},
            column_widths={"Image_Link": 15}
            )
        #Persons dataset on excel
        df_persons.write_excel(
            workbook=wb, 
            worksheet='Persons database',
            column_formats={"Image_Link": hyperlink_format},
            column_widths={"Image_Link": 15}
            )
    print(f"Excel file exported to {excel_file}")