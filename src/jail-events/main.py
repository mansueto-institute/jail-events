from pathlib import Path
from pdf_processing.page_functions import scrape_page
from pdf_processing.dictionary_functions import main as dictionary_cleaning
import json
import pickle
from tqdm import tqdm
import fitz, cv2, time
from preprocess.cleaning import pre_process_page
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import polars as pl
from analysis.analysis_handwritten import extract_ocr_confidence, generate_handwritten_report

def parse_image_dict(cleaned_img, key_id):
    """
    Parse a cleanded image into a dictionaries to json
    """
    cleaned_rep_dict = scrape_page(cleaned_img)
    cleaned_rep_dict["Report ID"] = key_id
    
    # Remove the problematic nested dictionary field
    if "Occurrence Dictionary" in cleaned_rep_dict:
        del cleaned_rep_dict["Occurrence Dictionary"]
    
    # Adding OCR analysis 
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
            "error_stage": None,
            "error_message": None
        }
        try:
            img = pre_process_page(page, dpi=dpi,
                                title_keyword=title_key)
            if img is None:
                log_entry.update({
                    "status": "failed",
                    "error_stage": "preprocessing",
                    "error_message": "Image preprocessing returned None"
                })
                processing_log.append(log_entry)
                #print(f"Page {i+1} in {pdf_stem} not preprocessed correctly")
                continue
            out_path = out_dir / f"{pdf_stem}_p{i+1}.png"
            cv2.imwrite(str(out_path), img)
            #print(f"saved {out_path.name}: {success}")
            
            try:
                page_dict = parse_image_dict(img, page_id)
                list_dicts.append(page_dict)
                log_entry.update({
                    "status": "success",
                    "error_stage": None,
                    "error_message": None
                })
                processing_log.append(log_entry)
                print(f"Successfully processed {page_id}")
                
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
                
                print(f"Completed {futures[future].name} - {len(result_dicts)} pages")
            except Exception as e:
                pdf_path = futures[future]
                print(f"Error processing {pdf_path.name}: {e}")
                #PDF - level error
                all_processing_logs.append({
                    "pdf_name": pdf_path.stem,
                    "page_number": None,
                    "page_id": f"{pdf_path.stem}_PDF_LEVEL_ERROR",
                    "status": "failed",
                    "error_stage": "pdf_level",
                    "error_message": f"PDF-level error: {str(e)}"
                })
                
    
    # for pdf in pdf_files:
    #     print(f"Processing pdf {pdf.name}")
    #     list_pages = process_single_pdf(pdf, dst_folder, dpi=dpi)
    #     list_docs.extend(list_pages)
    
    return list_docs, all_processing_logs


def main():
    # project paths
    #To run on all the pdfs:
    samples = Path(__file__).parent / "data/jails-data/raw"
    processed = Path(__file__).parent / "data/jails-data/processed"
    out_data = Path(__file__).parent / "data/jails-data/output"
    out_analysis = Path(__file__).parent / "analysis"
    out_data.mkdir(parents=True, exist_ok=True)
    
    # Time cloking
    start_time = time.time()
    
    # First parse all the pdfs and parrse images
    all_dicts_list, processing_logs = process_all_pdfs(samples, processed, dpi=300)
    
    # report
    generate_handwritten_report(all_dicts_list, out_analysis, threshold=70)
    # Save data as a pickle
    backup_file = out_data / "jails_pdfs_backup.pkl"
    with open(backup_file, "wb") as f:
        pickle.dump(all_dicts_list, f)
    print(f"Saved backup to {backup_file}")
    
    out_parquet = out_data / "jails_pdfs.parquet"
    df = pl.DataFrame(all_dicts_list)
    df.write_parquet(out_parquet)
    
    #log of errors
    log_parquet = out_data / "processing_logs.parquet"
    log_df = pl.DataFrame(processing_logs)
    log_df.write_parquet(log_parquet)
    
    print("\n=== PROCESSING SUMMARY ===")
    summary = log_df.group_by("status").agg(pl.len().alias("count"))
    for row in summary.iter_rows(named=True):
        print(f"{row['status'].title()}: {row['count']} pages")
    
    #Confidence analysis
    processing_time = time.time() - start_time
    
    print(f"Processed {len(all_dicts_list)} records in {processing_time:.1f}s, {processing_time/60:.1f} min")
    
    #DEBUGS:
    #image UO - FOIA December 2022 not preprocessed correctly
    #image UO - FOIA February 2019 not preprocessed correctly
    #image UO - JDSU (August 2022) not preprocessed correctly
    #Error processing UO - FOIA May 2019.pdf: unsupported operand type(s) for -: 'NoneType' and 'float'
    
    
if __name__ == "__main__":
    main()