from pathlib import Path
from pdf_processing.page_functions import scrape_page
from pdf_processing.dictionary_functions import main as dictionary_cleaning
import json
from tqdm import tqdm
import fitz, cv2, time
from preprocess.cleaning import pre_process_page

def parse_image_dict(cleaned_img, key_id):
    """
    Parse a cleanded image into a dictionaries to json
    """
    cleaned_rep_dict = scrape_page(cleaned_img)
    cleaned_rep_dict["Report ID"] = key_id
    return cleaned_rep_dict

def process_single_pdf(pdf_path: Path, out_dir: Path, dpi: int=300,
                       title_key: str = "REPORT EXTRAORDINARY UNUSUAL"):
    """
    Process of all the pages in a single pdf and return list dicrionaries
    """
    
    doc = fitz.open(pdf_path)
    pdf_stem = pdf_path.stem
    list_dicts = []
    for i, page in enumerate(doc):
        img = pre_process_page(page, dpi=dpi,
                               title_keyword=title_key)
        if img is None:
            print(f"image {pdf_stem} nor preprocessed correctly")
            continue
        out_path = out_dir / f"{pdf_stem}_p{i+1}.png"
        success = cv2.imwrite(str(out_path), img)
        print(f"saved {out_path.name}: {success}")
        dict = parse_image_dict(img, f"{pdf_stem}_p{i+1}")
        list_dicts.append(dict)
    
    doc.close()
    return list_dicts
        

def process_all_pdfs(src_folder: Path, dst_folder: Path, dpi: int = 300):
    """
    Process all PDFS in Folder and return a list of dicts
    """
    dst_folder.mkdir(parents=True, exist_ok=True)
    pdf_files = list(src_folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files in folder")
        return []
    
    list_docs = []
    for pdf in pdf_files:
        print(f"Processing pdf {pdf.name}")
        list_pages = process_single_pdf(pdf, dst_folder, dpi=dpi)
        list_docs.extend(list_pages)
    
    return list_docs


def main():
    # project paths
    samples = Path(__file__).parent / "data/jails-data/samples"
    processed = Path(__file__).parent / "data/jails-data/processed"
    out_data = Path(__file__).parent / "data/jails-data/output"
    out_data.mkdir(parents=True, exist_ok=True)
    
    # First parse all the pdfs and parrse images
    all_dicts_list = process_all_pdfs(samples, processed, dpi=300)
    out_json = out_data / "jails_pdfs.json"

    with open(out_json, "w") as json_file:
        json.dump(all_dicts_list, json_file, indent=2)
    print(f"Saved {len(all_dicts_list)} records to {out_json}")
    
if __name__ == "__main__":
    main()