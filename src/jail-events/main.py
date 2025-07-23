import click
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

def parse_image_dict(cleaned_img, key_id, image_path, origin_page, dpi, title_key):
    """
    Parse a cleanded image into a dictionaries to json
    """
    cleaned_rep_dict = scrape_page(cleaned_img)
    # If return the no year found, del and process again
    if cleaned_rep_dict == "No year found":
        print(f"page {cleaned_img} not correct, no cropping")
        #delete image file
        image_path.unlink()
        img = pre_process_page(page = origin_page, reprocess= True)
        cleaned_rep_dict = scrape_page(cleaned_img)
        cleaned_rep_dict["process"] = "reprocess"
    else: 
        cleaned_rep_dict["process"] = "normal"
        
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
                page_dict = parse_image_dict(img, page_id, out_path, page,
                                             dpi, title_key)
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

@click.command()
@click.option("--mode",
              type=click.Choice(['full', 'sample', 'debug']), 
              default = 'full',
              help = 'Processing mode: full (all data 27,800 pages), sample (aprox 120 pages), debug (few problematic pages)')

def main(mode):
    """ Processing jail PDFs """
    
    click.echo(f"Running in {mode.upper} mode")
    
    # project paths
    out_data = Path(__file__).parent / "data/jails-data/output"
    out_analysis = Path(__file__).parent / "analysis/"
    out_data.mkdir(parents=True, exist_ok=True)
    
    if mode == 'full':
        samples = Path(__file__).parent / "data/jails-data/raw"
        processed = Path(__file__).parent / "data/jails-data/processed"
        suffix = "_full"
    elif mode == "sample":
        samples = Path(__file__).parent / "data/jails-data/samples"
        processed = Path(__file__).parent / "data/jails-data/processed"
        suffix = "_sample"
    elif mode == "debug":
        samples = Path(__file__).parent / "data/jails-data/samples/debug"
        processed = Path(__file__).parent / "data/jails-data/processed/debug_processed"
        suffix = "_debug"
        
    # Create output file paths
    out_parquet = out_data / f"jails_pdfs{suffix}.parquet"
    log_parquet = out_data / f"processing_logs{suffix}.parquet"
    backup_file = out_data / f"jails_pdfs_backup{suffix}.pkl"

    
    # Time cloking
    start_time = time.time()
    
    # First parse all the pdfs and parrse images
    all_dicts_list, processing_logs = process_all_pdfs(samples, processed, dpi=300)
    
    # report
    generate_handwritten_report(all_dicts_list, out_analysis, threshold=70)
    # Save data as a pickle
    with open(backup_file, "wb") as f:
        pickle.dump(all_dicts_list, f)
    print(f"Saved backup to {backup_file}")
    
    df = pl.DataFrame(all_dicts_list)
    df.write_parquet(out_parquet)
    
    #log of errors
    log_df = pl.DataFrame(processing_logs)
    log_df.write_parquet(log_parquet)
    processing_time = time.time() - start_time
    
    # Summary 
    click.echo("\n" + "="*50)
    click.echo("PROCESSING SUMMARY")
    click.echo("="*50)
    click.echo(f"Mode: {mode.upper()}")
    click.echo(f"Total pages attempted: {len(processing_logs)}")
    
    summary = log_df.group_by("status").agg(pl.len().alias("count"))
    for row in summary.iter_rows(named=True):
            status_color = 'green' if row['status'] == 'success' else 'red'
            click.echo(f"{row['status'].title()}: ", nl=False)
            click.secho(f"{row['count']} pages", fg=status_color)
    
    #Confidence analysis
    
    click.echo(f"Processing time: {processing_time:.1f}s ({processing_time/60:.1f} min)")

if __name__ == "__main__":
    main()