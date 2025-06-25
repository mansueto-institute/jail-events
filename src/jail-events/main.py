from pathlib import Path
from pdf_processing.page_functions import scrape_page
from pdf_processing.dictionary_functions import main as dictionary_cleaning
import json
from tqdm import tqdm
import fitz, cv2, time
from preprocess.cleaning import pre_process_page

def process_single_pdf(pdf_path: Path, out_dir: Path, dpi: int=300,
                       title_key: str = "REPORT EXTRAORDINARY UNUSUAL"):
    """
    Process all the pages in a single pdf
    """
    
    doc = fitz.open(pdf_path)
    pdf_stem = pdf_path.stem
    for i, page in enumerate(doc):
        img = pre_process_page(page, dpi=dpi, aligned=False,
                               title_keyword=title_key)
        out_path = out_dir / f"{pdf_stem}_p{i+1}.png"
        success = cv2.imwrite(str(out_path), img)
        print(f"saved {out_path.name}: {success}")
    
    doc.close()
        

def process_all_pdfs(src_folder: Path, dst_folder: Path, dpi: int = 300):
    """
    Process all PDFS in Folder
    """
    dst_folder.mkdir(parents=True, exist_ok=True)
    pdf_files = list(src_folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files in folder")

    for pdf in pdf_files:
        print(f"Processing pdf {pdf.name}")
        process_single_pdf(pdf, dst_folder, dpi=dpi)


def main():
    samples = Path(__file__).parent / "data/jails-data/samples"
    processed = Path(__file__).parent / "data/jails-data/processed"
    process_all_pdfs(samples, processed, dpi=300)

    print ("HELLO WOWWWWWWWWWWWWWWWWWWW")

    dictionary_list = []
    id_number = 1
    images_folder = Path(__file__).parent / "data/jails-data/processed/aligned"
    for image_path in list(images_folder.glob("*.png")):
        uncleaned_report_dict = scrape_page(image_path)
        #cleaned_report_dict = dictionary_cleaning(uncleaned_report_dict)
        uncleaned_report_dict["Report ID"] = id_number
        dictionary_list.append(uncleaned_report_dict)
        id_number += 1

    output_path = Path(__file__).resolve().parent / "output" / "output.json"

    with open(output_path, "w") as json_file:
        json.dump(dictionary_list, json_file)

if __name__ == "__main__":
    main()