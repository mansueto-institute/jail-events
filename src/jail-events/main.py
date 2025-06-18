from pathlib import Path
from pdf_processing.page_functions import main as page_scraping
from pdf_processing.dictionary_functions import main as dictionary_cleaning
import json

images_folder = Path("Add address here")

def main():
    dictionary_list = []
    id_number = 1
    images_folder = None
    for image_path in images_folder.glob("*.png"):
        uncleaned_report_dict = page_scraping(image_path)
        cleaned_report_dict = dictionary_cleaning(uncleaned_report_dict)
        cleaned_report_dict["Report ID"] = id_number
        dictionary_list.append(cleaned_report_dict)
        id_number += 1

    with open("output.json", "w") as json_file:
        json.dump(dictionary_list, json_file)

