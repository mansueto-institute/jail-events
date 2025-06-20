import fitz
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json

from preprocess.cleaning import pre_process_page
from pdf_processing.processing_functions import (
    get_roi, blur_edge_contours, basic_text_line, 
    basic_box_check, yes_no_box_check
)

class JailReportProcessor:
    def __init__(self, 
                 canvas_size: Tuple[int,int] = (2550, 3300),
                 dpi: int = 300):
        self.canvas_size = canvas_size
        self.dpi = dpi
        
        # Field coordinates for STANDARDIZED images (after preprocessing)
        self.field_coords = {
            "facility_type": ((1320, 395), (1950, 720)),
            "facility_name": ((405, 825), (1650, 975)),
            "phone_number": ((1920, 825), (2250, 975)),
            "address": ((315, 990), (2250, 1050)),
            "date": ((510, 1095), (1260, 1200)),
            "time": ((1650, 1095), (2100, 1200)),
            "am_pm": ((2100, 1095), (2475, 1200)),
            "occurrence_area": ((510, 1238), (2475, 1500)),
            "table_area": ((75, 1500), (2400, 2100)),
            "injuries": ((450, 2070), (2400, 2175)),
            "resulting_death": ((525, 2175), (2400, 2295)),
            # more fields?
        }

    def process_pdf_page(self, page: fitz.Page, title_keyword: str = "ILLINOIS DEPARTMENT") -> Dict:
        """
        Complete pipeline: preprocess + extract data
        """
        # Step 1: Clean and standardize the image
        standardized_img = pre_process_page(
            page, 
            dpi=self.dpi, 
            aligned=True,
            title_keyword=title_keyword
        )
        
        # Step 2: Extract data from standardized image
        extracted_data = self.extract_all_fields(standardized_img)
        
        return {
            "standardized_image": standardized_img,
            "extracted_data": extracted_data
        }

    def extract_all_fields(self, cv2_image: np.ndarray) -> Dict:
        """Extract all form fields from preprocessed image"""
        page_dict = {}
        
        # Basic text fields
        page_dict["facility_name"] = self.get_facility_name(cv2_image)
        page_dict["phone_number"] = self.get_facility_phone(cv2_image)
        page_dict["address"] = self.get_address(cv2_image)
        page_dict["date"] = self.get_date(cv2_image)
        page_dict["time"] = self.get_time(cv2_image)
        
        # Checkbox fields
        page_dict["facility_type"] = self.get_facility_type(cv2_image)
        page_dict["am_pm"] = self.get_am_pm(cv2_image)
        page_dict["injuries"] = self.get_injuries(cv2_image)
        page_dict["resulting_death"] = self.get_resulting_death(cv2_image)
        
        # Complex fields
        page_dict["occurrence_dict"] = self.get_occurrence_dict(cv2_image)
        page_dict["table_contents"] = self.get_table(cv2_image)
        
        # Conditional fields (only if death occurred)
        if page_dict.get("resulting_death") == "Yes":
            page_dict.update(self.get_deceased_info(cv2_image))
            
        return page_dict

    # Refactored extraction methods using your existing logic
    def get_facility_name(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["facility_name"])
        return basic_text_line(roi).strip()

    def get_facility_phone(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["phone_number"])
        return basic_text_line(roi).strip()

    def get_address(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["address"])
        return basic_text_line(roi).strip()

    def get_date(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["date"])
        return basic_text_line(roi).strip()

    def get_time(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["time"])
        return basic_text_line(roi).strip()

    def get_facility_type(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["facility_type"])
        contours = blur_edge_contours(roi)
        return basic_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=80)

    def get_am_pm(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["am_pm"])
        contours = blur_edge_contours(roi)
        return basic_box_check(roi, contours, adjust_fill_ratio=0.3, adjust_width=100)

    def get_occurrence_dict(self, cv2_image: np.ndarray) -> Dict:
        """Your complex occurrence detection logic"""
        type_start_point, type_end_point = self.field_coords["occurrence_area"]
        # ... 
        return {}  # Placeholder

    def get_table(self, cv2_image: np.ndarray) -> List[str]:
        roi = get_roi(cv2_image, *self.field_coords["table_area"])
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        # ... 
        return []  # Placeholder

    def get_injuries(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["injuries"])
        contours = blur_edge_contours(roi)
        return yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

    def get_resulting_death(self, cv2_image: np.ndarray) -> str:
        roi = get_roi(cv2_image, *self.field_coords["resulting_death"])
        contours = blur_edge_contours(roi)
        return basic_box_check(roi, contours, adjust_fill_ratio=0.25, adjust_width=75)

    def get_deceased_info(self, cv2_image: np.ndarray) -> Dict:
        """Extract all deceased-related information"""
        return {
            "deceased_cause_date_time": "N/A",  
            "deceased_suicide_watch": "N/A",
            "deceased_reporter": "N/A", 
            "deceased_examined": "N/A",
            "deceased_illness": "N/A"
        }

def process_batch_pdfs(src_folder: Path, output_folder: Path):
    """Process multiple PDFs and save results"""
    processor = JailReportProcessor()
    output_folder.mkdir(parents=True, exist_ok=True)
    
    for pdf_path in src_folder.glob("*.pdf"):
        print(f"Processing {pdf_path.name}")
        doc = fitz.open(str(pdf_path))
        
        all_pages_data = []
        for page_num, page in enumerate(doc):
            result = processor.process_pdf_page(page)
            
            # Save standardized image
            img_path = output_folder / f"{pdf_path.stem}_p{page_num+1}.png"
            cv2.imwrite(str(img_path), result["standardized_image"])
            
            # Collect extracted data
            all_pages_data.append({
                "page": page_num + 1,
                "data": result["extracted_data"]
            })
        
        # Save extracted data as JSON
        json_path = output_folder / f"{pdf_path.stem}_data.json" 
        with open(json_path, 'w') as f:
            json.dump(all_pages_data, f, indent=2)
        
        doc.close()
        print(f"Saved images and JSON for {pdf_path.name}")

if __name__ == "__main__":
    src = Path("data/jails-data/samples")
    out = Path("data/jails-data/processed")
    process_batch_pdfs(src, out)