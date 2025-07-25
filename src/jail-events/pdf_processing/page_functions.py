import pytesseract
import pdf2image
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt
import jellyfish
from . import processing_functions as pf

#pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

class PageParsing:

    def __init__(self, cv2_image):
        
        self.cv2_image = cv2_image
        self.coordinate_dict = {"Facility Type": "NA"}
        self.page_dict = {"Deceased Name": "N/A",
             "Deceased Cause": "N/A",
             "Deceased Date and Time": "N/A",
             "Deceased on Suicide Watch": "N/A",
             "Deceased Reporter": "N/A",
             "Deceased Examined by Physician": "N/A",
             "Deceased Signs of Illness": "N/A"
    } #initializing dictionary without conditional values at first
        self.cook_county = False
        self.cook_county_running_y = 0

    def get_form_type(self):
        """
        Performs an initial scan of the document to determine its years and if its Cook County, assigns dictionary of coordinates for points
        """
        roi = pf.get_roi(self.cv2_image, (2100, 2900), (2550, 3300))
        text = pf.basic_text_line(roi)

        format_test = re.search(r"\d+", text)
        if not format_test:
            self.coordinate_dict = "No year found"
            return

        test_2002 = re.search("2002", text)

        if test_2002:
            new_coordinate_dict = {"Facility Type": ((1300, 300), (1950, 580)),
                                "RD Number": ((1300,540),(2550,700)),
                                "Facility Name": ((50, 650), (1625, 850)),
                                "Phone Number": ((1625, 650), (2450, 850)),
                                "Address": ((50, 800), (2400, 950)),
                                "Date": ((25, 950), (1200, 1100)),
                                "Time of Day": ((1225, 950), (2200, 1100)),
                                "AM or PM": ((2170, 1000), (2500, 1100)),
                                "Occurrence Dictionary": ((300, 1075), (2475, 1400)),
                                "Table Contents": ((0, 1450), (2550, 2025)),
                                "Injuries?": ((50, 2050), (2550, 2200)),
                                "Resulting Death?": ((50, 2200), (2450, 2300)),
                                "Deceased Name": ((50,2265),(2450,2375)),
                                "Deceased Cause": ((50,2375),(2450,2475)),
                                "Deceased Date and Time": ((50,2475),(2550,2575)),
                                "Deceased on Suicide Watch": ((50, 2575), (2400, 2675)),
                                "Deceased Reporter": ((50, 2675), (2500, 2775)),
                                "Deceased Examined by Physician": ((50, 2765), (2550, 2875)),
                                "Deceased Signs of Illness": ((50,2865), (2500,2975))}
            roi = pf.get_roi(self.cv2_image, (100, 300), (1200, 800))
            new_text = pf.basic_text_line(roi)
            test_gym = re.search("Second Floor Gymnasium", new_text)
            if test_gym:
                new_coordinate_dict["Injuries?"] = ((50,2125), (2550, 2275))
                new_coordinate_dict["Resulting Death?"] = ((50, 2225), (2450, 2325))
                new_coordinate_dict["Deceased Name"] = ((50,2290),(2450,2400))
                new_coordinate_dict["Deceased Cause"] = ((50,2400),(2450,2500))
                new_coordinate_dict["Deceased Date and Time"] = ((50,2500),(2550,2600))
                new_coordinate_dict["Deceased on Suicide Watch"] = ((50, 2600), (2400, 2700))
                new_coordinate_dict["Deceased Reporter"] = ((50, 2700), (2500, 2800))
                new_coordinate_dict["Deceased Examined by Physician"] = ((50, 2790), (2550, 2900))
                new_coordinate_dict["Deceased Signs of Illness"] = ((50,2890), (2500,3000))
        else:
            self.coordinate_dict["Facility Name"] = ((50, 675), (1625, 850))
            self.get_facility_name()
            facility = self.page_dict["Facility Name"]
            test_facility = re.search("Cook County", facility, re.IGNORECASE)
            if test_facility:
                self.cook_county = True
                self.page_dict["Cook County?"] = "Cook County" #delete this for final product?
                new_coordinate_dict = {"Facility Type": ((1300, 300), (1950, 580)),
                                    "RD Number": ((1300,550),(2500,700)),
                                    "Facility Name": ((50, 675), (1625, 850)),
                                    "Phone Number": ((1650, 655), (2500, 850)),
                                    "Address": ((50, 825), (2400, 925)),
                                    "Date": ((25, 950), (1250, 1100)),
                                    "Time of Day": ((1250, 1000), (2500, 1100)),
                                    "AM or PM": ((2170, 1000), (2500, 1100)), #doesn't need AM or PM part
                                    "Occurrence Dictionary": ((300, 1050), (2500, 1450)), #up to here is standard
                                    "Table Contents": ((0, 1400), (2550, 2700)),
                }

            else:
                new_coordinate_dict = {"Facility Type": ((1300, 300), (1950, 580)),
                                        "RD Number": ((1300,525),(2550,700)),
                                        "Facility Name": ((50, 675), (1625, 850)),
                                        "Phone Number": ((1650, 655), (2500, 850)),
                                        "Address": ((50, 800), (2500, 950)),
                                        "Date": ((25, 950), (1250, 1100)),
                                        "Time of Day": ((1225, 950), (2170, 1100)),
                                        "AM or PM": ((2170, 1000), (2500, 1100)),
                                        "Occurrence Dictionary": ((300, 1100), (2475, 1400)),
                                        "Table Contents": ((0, 1450), (2550, 2100)),
                                        "Injuries?": ((50, 2050), (2550, 2200)),
                                        "Resulting Death?": ((50, 2150), (2450, 2250)),
                                        "Resulting Death?": ((50, 2150), (2450, 2250)),
                                        "Deceased Name": ((50,2250),(2450,2350)),
                                        "Deceased Cause": ((50,2350),(2450,2450)),
                                        "Deceased Date and Time": ((50,2450),(2450,2550)),
                                        "Deceased Cause, Date, and Time": ((50, 2300), (2450, 2575)),
                                        "Deceased on Suicide Watch": ((50, 2550), (2400, 2675)),
                                        "Deceased Reporter": ((50, 2625), (2500, 2775)),
                                        "Deceased Examined by Physician": ((50, 2740), (2550, 2860)),
                                        "Deceased Signs of Illness": ((150, 2860), (2550,2960)),
                                        "Deceased Examined by Physician": ((50, 2740), (2550, 2860)),
                                        "Deceased Signs of Illness": ((150, 2860), (2550,2960))}
                
        self.coordinate_dict = new_coordinate_dict

    def get_facility_type(self):
        """
        Retrieves first few letters of facility type, to be processed later
        """
        points = self.coordinate_dict["Facility Type"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi, 5)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.1, adjust_width=160, adjust_box_min_box_area=1500)

        self.page_dict["Facility Type"] = text

    def get_rd_number(self):
        """
        Retrieves case number. May be inconsistent due to stamps.
        """
        points = self.coordinate_dict["RD Number"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["RD Number"] = text

    def get_facility_name(self):
        """
        Retrieves full name of the facility
        """
        points = self.coordinate_dict["Facility Name"]
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
        """
        Retrieves date of incident. 
        """
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

        if self.cook_county:
            self.page_dict["AM or PM"] = "Check time, no AM or PM for Cook County"
        else:
            points = self.coordinate_dict["AM or PM"]
            roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
            contours = pf.blur_edge_contours(roi, 1.5)
            text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.1, adjust_width=100, adjust_box_min_box_area=500)

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
        contours = pf.blur_edge_contours(roi, 1.5)
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
            if contour.ndim == 3:
                contour = contour[:,0]
            carea = ((np.max(contour[:,0]) - np.min(contour[:,0]))) * (np.max(contour[:,1]) - np.min(contour[:,1])) #gets comments from divij
            s = ""
            if (carea > 800) and (carea < 2000):
                extent = cv2.contourArea(contour) / carea #rules out letters being selected
                if extent > 0.9:
                    s = "**"
            if s == "**":
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                if 0.5 < aspect_ratio < 2.0:
                    cropped_rect = roi[y : (y + h), x : (x + w)]
                    gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
                    _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
                    # Crop inside to ignore border (e.g. 10% margin)
                    margin = int(min(w, h) * 0.1)
                    inner = binary[margin:h-margin, margin:w-margin]
                    fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
                    if x == 0 or y == 0 or w == 0 or h == 0:
                        break
                    if y < roi_height*0.3 or (x > roi_width*0.6 and y > roi_height*0.6):
                        text_offset_x = 20  # pixels to skip after box
                        text_width = 600   # width of text region to extract
                        text_roi = roi[y-15:y+h+10, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        if text_roi.size == 0:
                            break
                        # cv2.imshow("Contours Visualization", text_roi)
                        # cv2.waitKey(0)
                        # cv2.destroyAllWindows()
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[str((x,y))] = [text, fill_ratio]
                    else:
                        text_offset_x = 20  # pixels to skip after box
                        text_width = 300    # width of text region to extract
                        text_roi = roi[y-10:y+h+10, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        if text_roi.size == 0:
                            #print ("Error creating ROI")
                            break
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[str((x,y))] = [text, fill_ratio]

        # cv2.imshow("Contours Visualization", roi)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        self.page_dict["Occurrence Dictionary"] = return_dict #returns dictionary of coordinate of the checkbox as keys then the text content and the fill ratio

    def get_table(self):

        """Scans the prisoner table and returns of list of all elements. Needs to be cleaned by prisoner for the final data."""
        points = self.coordinate_dict["Table Contents"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(~gray, 255, 
                                    cv2.ADAPTIVE_THRESH_MEAN_C, 
                                    cv2.THRESH_BINARY, 15, -2)
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)) #getting lines of the table
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_y = 0
        for cnt in contours: #finding the lowest horiztonal line of the table
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50:  # Filter out noise: adjust threshold as needed
                line_strip = vertical_lines[y:y+h, x:x+w]
                vertical_intersections = cv2.countNonZero(line_strip)
                if vertical_intersections > 0:
                    max_y = max(max_y, y + h)

        roi_trimmed = roi[:max_y, :]

        if roi_trimmed.size == 0:
            self.page_dict["Table Contents"] = ["Bad parse"]
            return

        #redoing the steps with the trimmed table
        gray_trimmed = cv2.cvtColor(roi_trimmed, cv2.COLOR_BGR2GRAY)

        binary_trimmed = cv2.adaptiveThreshold(~gray_trimmed, 255, 
                                            cv2.ADAPTIVE_THRESH_MEAN_C, 
                                            cv2.THRESH_BINARY, 15, -2)

        horizontal_lines_trimmed = cv2.morphologyEx(binary_trimmed, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines_trimmed = cv2.morphologyEx(binary_trimmed, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        #ensuring small vertical lines (letters) aren't cut out
        vertical_contours, _ = cv2.findContours(vertical_lines_trimmed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_height = 50  

        for cnt in vertical_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < min_height:
                cv2.drawContours(vertical_lines_trimmed, [cnt], -1, 0, -1)

        lines_trimmed = cv2.add(horizontal_lines_trimmed, vertical_lines_trimmed)
        cleaned_trimmed = cv2.subtract(binary_trimmed, lines_trimmed)

        text = pytesseract.image_to_string(cleaned_trimmed, config='--psm 12')

        prohibited = ["Detainees Involved", "Name", "Date of Birth", "Date Confined", "Arresting Charge"]

        cells = []

        stripped_text = text.strip().splitlines()
        pattern_punctuation = r"[.,!_|-]" #takes each element of the text, filters, turns into list
        for element in stripped_text:
            cleaned_element = re.sub(pattern_punctuation, '', element)
            highest_jw = 0
            for test in prohibited:
                jw = jellyfish.jaro_similarity(test, cleaned_element)
                if jw > highest_jw:
                    highest_jw = jw
            if cleaned_element and len(cleaned_element) > 4 and highest_jw < 0.8: #can adjust jw
                cells.append(element)

        self.page_dict["Table Contents"] = cells

    def get_injuries(self):
        """
        Retrieves recorded injuries
        """
        points = self.coordinate_dict["Injuries?"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi, 1.5)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=2000)
        pattern = r"\bno\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = "No injuries"  

        self.page_dict["Injuries?"] = text

    def get_resulting_death(self):
        """
        Retrieves if there was a death that occured, which may result in all below functions being called.
        """
        points = self.coordinate_dict["Resulting Death?"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi, 5)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.1, adjust_width=100, adjust_box_min_box_area=1250)
        pattern = r"yes"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = "Yes"  

        self.page_dict["Resulting Death?"] = text

    def get_deceased_name(self):
        points = self.coordinate_dict["Deceased Name"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Deceased Name"] = text

    def get_deceased_cause(self):
        points = self.coordinate_dict["Deceased Cause"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Deceased Cause"] = text

    def get_deceased_date_time(self):
        points = self.coordinate_dict["Deceased Date and Time"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        text = pf.basic_text_line(roi)

        self.page_dict["Deceased Date and Time"] = text

    def get_suicide_watch(self):
        """
        Retrieves whether the deceased was on suicide watch
        """
        points = self.coordinate_dict["Deceased on Suicide Watch"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1]) 
        contours = pf.blur_edge_contours(roi, 1.5)
        text = pf.basic_box_check(roi, contours, adjust_fill_ratio=0.1, adjust_width=60, adjust_box_min_box_area=1500)

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
        contours = pf.blur_edge_contours(roi, 1.5)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

        self.page_dict["Deceased Examined by Physician"] = text

    def get_deceased_illness(self):
        """
        Returns whether the deceased displayed signs of illness.
        """
        points = self.coordinate_dict["Deceased Signs of Illness"]
        roi = pf.get_roi(self.cv2_image, points[0], points[1])
        contours = pf.blur_edge_contours(roi, 1.5)
        text = pf.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1200)
        if text != "No":
            new_roi = pf.get_roi(self.cv2_image, (50,points[0][1]+100), (2500,points[1][1]+100))
            new_roi = pf.get_roi(self.cv2_image, (50,points[0][1]+100), (2500,points[1][1]+100))
            follow_up_text = pf.basic_text_line(new_roi)
            text += follow_up_text

        self.page_dict["Deceased Signs of Illness"] = text
    
    def cook_county_parse(self):
        """
        Parses the table then does a full rip of injury and death information for Cook County Prison format
        """
        self.cook_county_table()
        self.cook_county_coordinates()
        self.get_injuries()
        self.get_resulting_death()
        if self.page_dict["Resulting Death?"] == "Yes":
            self.page_dict["Resulting Death?"] = "Yes, check the report, Cook County"
    
    def cook_county_table(self):
        """
        Gets table with unique considerations to how Cook County tables are formatted
        """

        points = self.coordinate_dict["Table Contents"]
        # cv2.imshow("Tableraw", self.cv2_image)
        roi = pf.get_roi(self.cv2_image, points[0], points[1])

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(~gray, 255, 
                                    cv2.ADAPTIVE_THRESH_MEAN_C, 
                                    cv2.THRESH_BINARY, 15, -2)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)) #getting lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_y = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50:  # Filter out noise: adjust threshold as needed
                line_strip = vertical_lines[y:y+h, x:x+w]
                vertical_intersections = cv2.countNonZero(line_strip)
                if vertical_intersections > 0:
                    max_y = max(max_y, y + h)

        roi_trimmed = roi[:max_y, :]

        gray_trimmed = cv2.cvtColor(roi_trimmed, cv2.COLOR_BGR2GRAY)

        binary_trimmed = cv2.adaptiveThreshold(~gray_trimmed, 255, 
                                            cv2.ADAPTIVE_THRESH_MEAN_C, 
                                            cv2.THRESH_BINARY, 15, -2)

        horizontal_lines_trimmed = cv2.morphologyEx(binary_trimmed, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines_trimmed = cv2.morphologyEx(binary_trimmed, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        vertical_contours, _ = cv2.findContours(vertical_lines_trimmed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_height = 50  

        for cnt in vertical_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < min_height:
                cv2.drawContours(vertical_lines_trimmed, [cnt], -1, 0, -1)

        lines_trimmed = cv2.add(horizontal_lines_trimmed, vertical_lines_trimmed)
        cleaned_trimmed = cv2.subtract(binary_trimmed, lines_trimmed)

        text = pytesseract.image_to_string(cleaned_trimmed, config='--psm 12')

        prohibited = ["Detainees Involved", "Name", "Date of Birth", "Date Confined", "Arresting Charge"]

        cells = []
        stripped_text = text.strip().splitlines()
        pattern_punctuation = r"[^a-zA-Z0-9/]"
        for element in stripped_text:
            cleaned_element = re.sub(pattern_punctuation, '', element)
            highest_jw = 0
            for test in prohibited:
                jw = jellyfish.jaro_similarity(test, cleaned_element)
                if jw > highest_jw:
                    highest_jw = jw
            if cleaned_element and len(cleaned_element) > 4 and highest_jw < 0.8: #can adjust jw
                cells.append(element)

        self.page_dict["Table Contents"] = cells
        self.running_y = points[0][1] + max_y

    def cook_county_coordinates(self):
        """
        Gets the last consistent coordinates for a Cook County report.
        """
        self.coordinate_dict["Injuries?"] = ((50, self.running_y), (2550, self.running_y + 150))
        self.running_y = self.coordinate_dict["Injuries?"][1][1]
        self.coordinate_dict["Resulting Death?"] = ((50, self.running_y), (2450, self.running_y + 100))
        self.running_y = self.coordinate_dict["Resulting Death?"][1][1]

    def clean_occurrences(self):
        """
        Takes dictionary of occurrences and finds which boxes are filled.
        """
        final_list = []
        sorting_dict = {}
        occurrence_dict = self.page_dict["Occurrence Dictionary"]
        for coordinates, box_list in occurrence_dict.items(): #turn list of coordinates into a simpler dictionary
            sorting_dict[box_list[0]] = box_list[1]
        if not sorting_dict: #what to return if nothing found/bad parse
            self.page_dict["Occurrence"] = final_list
            return
        average_fill = np.mean(list(sorting_dict.values())) #get mean fill ratios 
        for occurrence, fill_ratio in sorting_dict.items():
            if fill_ratio > (average_fill + (average_fill*0.5)):
                final_list.append(occurrence)
        self.page_dict["Occurrence"] = final_list

def scrape_page(image):
    #cv2_image = cv2.imread(str(image_path))
    cv2_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    page_parser = PageParsing(cv2_image)
    page_parser.get_form_type()
    if page_parser.coordinate_dict == "No year found":
        return "No year found"
    page_parser.get_facility_type()
    page_parser.get_rd_number()
    page_parser.get_facility_name()
    page_parser.get_facility_phone()
    page_parser.get_address()
    page_parser.get_date()
    page_parser.get_time()
    page_parser.get_am_pm()
    page_parser.get_occurrence_dict()
    page_parser.clean_occurrences()
    #page_parser.page_dict.del delete the occurrence dict key after getting it clean
    if page_parser.cook_county:
        page_parser.cook_county_parse()
    else:
        page_parser.get_table()
        page_parser.get_injuries()
        page_parser.get_resulting_death()
        if page_parser.page_dict["Resulting Death?"] == "Yes":
            page_parser.get_deceased_name()
            page_parser.get_deceased_cause()
            page_parser.get_deceased_date_time()
            page_parser.get_suicide_watch()
            page_parser.get_reported()
            page_parser.get_deceased_examined()
            page_parser.get_deceased_illness()
    #test
    return (page_parser.page_dict)

if __name__ == "__main__":
    image_path = Path(__file__).resolve().parents[2] / "jail-events" / "data" / "jails-data" / "processed" / "UO - FOIA December 2019_p140.png"
    print (scrape_page(image_path))