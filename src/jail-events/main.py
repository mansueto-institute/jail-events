from pathlib import Path
from pdf_processing.page_functions import main as page_scraping
from pdf_processing.dictionary_functions import main as dictionary_cleaning

images_folder = Path("Add address here")

def main():
    print("Hello from jail-events!")
    images_folder = None
    for image_path in images_folder.glob("*.png"):
        uncleaned_report_dict = page_scraping(image_path)
        cleaned_report_dict = dictionary_cleaning(uncleaned_report_dict)