import pytesseract
import pdf2image
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt
import processing_functions as pf

#pdf_processing.

"""
TO DO
get start of table for Cook County, can find the end?
increase contrast
"""

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

class PageParsing:

    def __init__(self, cv2_image):
        
        self.cv2_image = cv2_image
        self.coordinate_dict = {"Facility Type": "NA"}
        self.page_dict = {"Deceased Cause, Date, and Time": "N/A",
             "Deceased on Suicide Watch": "N/A",
             "Deceased Reporter": "N/A",
             "Deceased Examined by Physician": "N/A",
             "Deceased Signs of Illness": "N/A"
    } #initializing dictionary without conditional values at first
        self.cook_county = False

    def get_form_type(self):
        """
        Performs an initial scan of the document to determine its years and if its Cook County, assigns dictionary of coordinates for points
        """
        roi = pf.get_roi(self.cv2_image, (2100, 3000), (2500, 3300))
        text = pf.basic_text_line(roi)

        test_2002 = re.search("2002", text)

        if test_2002:
            new_coordinate_dict = {"Facility Type": ((1000, 300), (1950, 580)),
                                "Facility Name": ((50, 650), (1625, 850)),
                                "Phone Number": ((1625, 650), (2450, 850)),
                                "Address": ((50, 800), (2400, 950)),
                                "Date": ((25, 950), (1200, 1100)),
                                "Time of Day": ((1225, 950), (2200, 1100)),
                                "AM or PM": ((2170, 1000), (2500, 1100)),
                                "Occurrence Dictionary": ((430, 1075), (2475, 1400)),
                                "Table Contents": ((25, 1500), (2375, 2025)),
                                "Injuries?": ((50, 1950), (2550, 2100)),
                                "Resulting Death?": ((50, 2075), (2450, 2175)),
                                "Deceased Cause, Date, and Time": ((50, 2200), (2450, 2475)),
                                "Deceased on Suicide Watch": ((50, 2450), (2400, 2550)),
                                "Deceased Reporter": ((50, 2525), (2500, 2675)),
                                "Deceased Examined by Physician": ((50, 2625), (2450, 2750)),
                                "Deceased Signs of Illness": ((50,2750), (2500,2850))}
        else:
            self.coordinate_dict["Facility Name"] = ((50, 675), (1625, 850))
            facility = self.get_facility_name()
            print (facility)
            test_facility = re.search("Cook County", facility)
            if test_facility:
                self.cook_county = True
                new_coordinate_dict = {"Facility Type": ((1050, 300), (1950, 580)),
                                    "Facility Name": ((50, 675), (1625, 850)),
                                    "Phone Number": ((1650, 655), (2500, 850)),
                                    "Address": ((50, 825), (2400, 925)),
                                    "Date": ((25, 950), (1250, 1100)),
                                    "Time of Day": ((1250, 1000), (2500, 1100)),
                                    "AM or PM": ((2170, 1000), (2500, 1100)), #doesn't need AM or PM part
                                    "Occurrence Dictionary": ((430, 1100), (2475, 1400)), #up to here is standard
                }

            else:
                new_coordinate_dict = {"Facility Type": ((1050, 300), (1950, 580)),
                                        "Facility Name": ((50, 675), (1625, 850)),
                                        "Phone Number": ((1650, 655), (2500, 850)),
                                        "Address": ((50, 870), (2400, 950)),
                                        "Date": ((25, 950), (1250, 1100)),
                                        "Time of Day": ((1225, 950), (2170, 1100)),
                                        "AM or PM": ((2170, 1000), (2500, 1100)),
                                        "Occurrence Dictionary": ((430, 1100), (2475, 1400)),
                                        "Table Contents": ((25, 1450), (2450, 2100)),
                                        "Injuries?": ((50, 2100), (2550, 2200)),
                                        "Resulting Death?": ((50, 2200), (2450, 2300)),
                                        "Deceased Cause, Date, and Time": ((50, 2300), (2450, 2575)),
                                        "Deceased on Suicide Watch": ((50, 2575), (2400, 2675)),
                                        "Deceased Reporter": ((50, 2675), (2500, 2775)),
                                        "Deceased Examined by Physician": ((50, 2775), (2450, 2875)),
                                        "Deceased Signs of Illness": ((150, 2875), (2500,2975))}
                
        self.coordinate_dict = new_coordinate_dict

    def get_facility_type(self):
        """
        Retrieves first three letters of facility type, to be processed later
        """
        points = self.coordinate_dict["Facility Type"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) #what do we need to do again once we have the box?
        contours = pf.blur_edge_contours(roi)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=80)

        self.page_dict["Facility Type"] = text

    def get_facility_name(self):
        """
        Retrieves full name of the facility
        """
        points = self.coordinate_dict["Facility Name"]
        print (points)
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Facility Name"] = text

    def get_facility_phone(self):
        """
        Retrieves phone number to contact the facility
        """
        points = self.coordinate_dict["Phone Number"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Phone Number"] = text

    def get_address(self):
        """
        Retrieves street address for facility.
        """
        points = self.coordinate_dict["Address"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Address"] = text

    def get_date(self):
        """Retrieves date of incident. """
        points = self.coordinate_dict["Date"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Date"] = text

    def get_time(self):
        """
        Retrieves the raw tine of the incident. May be in either military or standard time.
        """
        points = self.coordinate_dict["Time of Day"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Time of Day"] = text

    def get_am_pm(self):
        """
        For incidents not in military time, retrieves whether they occured in the AM or PM
        """
        points = self.coordinate_dict["AM or PM"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        contours = pf.blur_edge_contours(roi)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.3, adjust_width=100)

        self.page_dict["AM or PM"] = text

    def get_occurrence_dict(self): #need to edit this down
        """
        Creates a dictionary of every possible occurence, text if applicable, and the fill ratio of its box for comparison.
        """
        
        type_start_point = self.coordinate_dict["Occurrence Dictionary"][0]
        type_end_point = self.coordinate_dict["Occurrence Dictionary"][1]

        x1 = min(type_start_point[0], type_end_point[0])
        x2 = max(type_start_point[0], type_end_point[0])
        y1 = min(type_start_point[1], type_end_point[1])
        y2 = max(type_start_point[1], type_end_point[1])

        roi_width = x2 - x1
        roi_height = y2 - y1

        return_dict = {}

        text = None
        roi = self.cv2_image[y1:y2, x1:x2]
        contours = pf.blur_edge_contours(roi)
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
            if contour.ndim == 3:
                contour = contour[:,0]
            carea = ((np.max(contour[:,0]) - np.min(contour[:,0]))) * (np.max(contour[:,1]) - np.min(contour[:,1])) #gets comments from divij
            s = ""
            if (carea > 1000) and (carea < 2000):
                s = "**"
            if s == "**":
                x, y, w, h = cv2.boundingRect(approx)
                area = cv2.contourArea(approx) 
                if 500 <= area <= 5000: #check if its a box
                    if x >= 0 and y >= 0 and x + w <= roi_width and y + h <= roi_height:
                        cropped_rect = roi[y : (y + h), x : (x + w)]
                        gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
                        _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
                        # Crop inside to ignore border (e.g. 10% margin)
                        margin = int(min(w, h) * 0.1)
                        inner = binary[margin:h-margin, margin:w-margin]
                        fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
                        if y < roi_height*0.3 or (x > roi_width*0.6 and y > roi_height*0.6):
                            text_offset_x = 15  # pixels to skip after box
                            text_width = 600   # width of text region to extract
                            text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                            text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                            _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                            text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                            return_dict[str((x,y))] = [text, fill_ratio]
                        else:
                            text_offset_x = 15  # pixels to skip after box
                            text_width = 120    # width of text region to extract
                            text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                            text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                            _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                            text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                            return_dict[str((x,y))] = [text, fill_ratio]

        self.page_dict["Occurrence Dictionary"] = return_dict #returns dictionary of coordinate of the checkbox as keys then the text content and the fill ratio

    def get_table(self):

        """Scans the prisoner table and returns of list of all elements. Needs to be cleaned by prisoner for the final data."""
        points = self.coordinate_dict["Table Contents"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(~gray, 255, 
                                    cv2.ADAPTIVE_THRESH_MEAN_C, 
                                    cv2.THRESH_BINARY, 15, -2)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
        lines = cv2.add(horizontal_lines, vertical_lines)
        cleaned = cv2.subtract(binary, lines)
        text = pytesseract.image_to_string(cleaned, config='--psm 12')

        cells = []
        stripped_text = text.strip().splitlines()
        prohibited = ["|"]
        for element in stripped_text:
            if element and element not in prohibited:
                cells.append(element)

        multiples = [4,8,12,16]
        for row in multiples:
            if len(cells) > row:
                if "|" in cells[row]:
                    for extra_charge in cells[row:]:
                        cells[row-1] += extra_charge
                    cells = cells[:row]

        self.page_dict["Table Contents"] = cells

    def get_injuries(self):
        """
        Retrieves recorded injuries
        """
        points = self.coordinate_dict["Injuries?"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

        self.page_dict["Injuries?"] = text

    def get_resulting_death(self):
        """
        Retrieves if there was a death that occured, which may result in all below functions being called.
        """
        points = self.coordinate_dict["Resulting Death?"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        contours = pf.blur_edge_contours(roi)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.15, adjust_width=75)    

        self.page_dict["Resulting Death?"] = text

    def get_deceased_cause_date_time(self):
        """
        Retirves name of deceased, caused of death, and the date and time
        """
        points = self.coordinate_dict["Deceased Cause, Date, and Time"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Deceased Cause, Date, and Time"] = text

    def get_suicide_watch(self):
        """
        Retrieves whether the deceased was on suicide watch
        """
        points = self.coordinate_dict["Deceased on Suicide Watch"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        contours = pf.blur_edge_contours(roi)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=60)

        self.page_dict["Deceased on Suicide Watch"] = text

    def get_reported(self):
        """
        Retrieves the name of the individual who reported the deceased.
        """
        points = self.coordinate_dict["Deceased Reporter"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Deceased Reporter"] = text

    def get_deceased_examined(self):
        """
        Returns whether the deceased was examined by a doctor and if so, when
        """
        points = self.coordinate_dict["Deceased Examined by Physician"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

        self.page_dict["Deceased Examined by Physician"] = text

    def get_deceased_illness(self):
        """
        Returns whether the deceased displayed signs of illness.
        """
        points = self.coordinate_dict["Deceased Signs of Illness"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1200)
        if text != "No":
            new_roi = pf.get_roi(self.cv2_image, (50,2875), (2500,3000))
            follow_up_text = pf.basic_text_line(new_roi)
            text += follow_up_text

        self.page_dict["Deceased Signs of Illness"] = text
    
    def cook_county_parse(self):
        """
        Parses the table then does a full rip of injury and death information for Cook County Prison format
        """
        #(25, 1450) table start 
        self.page_dict["Table Contents"] = 1
        self.page_dict["Cook County Rip"] = 2

def scrape_page(image_path):
    cv2_image = cv2.imread(str(image_path))
    cv2_image = cv2.cvtColor(np.array(cv2_image), cv2.COLOR_RGB2BGR)
    page_parser = PageParsing(cv2_image)
    page_parser.get_form_type()
    page_parser.get_facility_type()
    page_parser.get_facility_name()
    page_parser.get_facility_phone()
    page_parser.get_address()
    page_parser.get_date()
    page_parser.get_time()
    page_parser.get_am_pm()
    page_parser.get_occurrence_dict()
    if page_parser.cook_county:
        page_parser.cook_county_parse()
    else:
        page_parser.get_table()
        page_parser.get_injuries()
        page_parser.get_resulting_death()
        if page_parser.page_dict["Resulting Death?"] == "Yes":
            page_parser.get_deceased_cause_date_time()
            page_parser.get_suicide_watch()
            page_parser.get_reported()
            page_parser.get_deceased_examined()
            page_parser.get_deceased_illness()

    return (page_parser.page_dict)

if __name__ == "__main__":
    image_path = Path(__file__).resolve().parents[2] / "jail-events" / "data" / "jails-data" / "processed" / "aligned" / "Cook County Test_p1.png"
    print (scrape_page(image_path))