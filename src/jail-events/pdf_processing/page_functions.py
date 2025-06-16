import pytesseract
import pdf2image
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt
import processing_functions

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

page_dict = {"Deceased Cause, Date, and Time": "N/A",
             "Deceased on Suicide Watch": "N/A",
             "Deceased Reporter": "N/A",
             "Deceased Examined by Physician": "N/A",
             "Deceased Signs of Illness": "N/A"
} 

#initializing dictionary without conditional values at first

pdf_path = Path(__file__).resolve().parents[3] / "testing" / "normal_test.pdf"

doc = pdf2image.convert_from_path(pdf_path) #creates list object 

pil_image = doc[0]
cv2_image = np.array(pil_image)

cv2_image = cv2.cvtColor(np.array(cv2_image), cv2.COLOR_RGB2BGR)

'''
Assumes we are given the PDF with color and blur applied - should contours be applied first?

Do contours need to be defined each time?
'''

def get_facility_type():
    """
    Retrieves first three letters of facility type, to be processed later
    """
    roi = processing_functions.get_roi(cv2_image, (880, 330), (1300, 480)) #what do we need to do again once we have the box?
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=50)

    page_dict["Facility Type"] = text

def get_facility_name():
    """
    Retrieves full name of the facility
    """
    roi = processing_functions.get_roi(cv2_image, (270, 550), (1100, 650))
    text = processing_functions.basic_text_line(roi)

    page_dict["Facility Name"] = text

def get_facility_phone():
    """
    Retrieves phone number to contact the facility
    """
    roi = processing_functions.get_roi(cv2_image, (1280, 550), (1500, 650))
    text = processing_functions.basic_text_line(roi)

    page_dict["Phone Number"] = text

def get_address():
    """
    Retrieves street address for facility.
    """
    roi = processing_functions.get_roi(cv2_image, (210, 660), (1500, 700))
    text = processing_functions.basic_text_line(roi)

    page_dict["Address"] = text

def get_date():
    """Retrieves date of incident. """
    roi = processing_functions.get_roi(cv2_image, (340, 730), (840, 800))
    text = processing_functions.basic_text_line(roi)

    page_dict["Date"] = text

def get_time():
    """
    Retrieves the raw tine of the incident. May be in either military or standard time.
    """
    roi = processing_functions.get_roi(cv2_image, (1100, 730), (1400, 800))
    text = processing_functions.basic_text_line(roi)

    page_dict["Time of Day"] = text

def get_am_pm():
    """
    For incidents not in military time, retrieves whether they occured in the AM or PM
    """
    roi = processing_functions.get_roi(cv2_image, (1400, 730), (1650, 800)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=40)

    page_dict["AM or PM"] = text

def get_occurence_dict(): #need to edit this down
    """
    Creates a dictionary of every possible occurence, text if applicable, and the fill ratio of its box for comparison.
    """

    type_start_point = (340, 825)
    type_end_point = (1650, 1000)

    x1 = min(type_start_point[0], type_end_point[0])
    x2 = max(type_start_point[0], type_end_point[0])
    y1 = min(type_start_point[1], type_end_point[1])
    y2 = max(type_start_point[1], type_end_point[1])

    roi_width = x2 - x1
    roi_height = y2 - y1

    return_dict = {}

    text = None
    roi = cv2_image[y1:y2, x1:x2]
    height, width = roi.shape[:2]
    contours = processing_functions.blur_edge_contours(roi)
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(approx) 
            if 0.85 <= aspect_ratio <= 1.15 and 250 <= area <= 5000: #check if its a box
                if x >= 0 and y >= 0 and x + w <= roi_width and y + h <= roi_height:
                    cropped_rect = roi[y : (y + h), x : (x + w)]
                    gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
                    _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
                    # Crop inside to ignore border (e.g. 10% margin)
                    margin = int(min(w, h) * 0.1)
                    inner = binary[margin:h-margin, margin:w-margin]
                    fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
                    if (x < roi_width*0.05 and y < roi_height*0.05) or (x < roi_width*0.6 and y < roi_height*0.05) or (x > roi_width*0.6 and y > roi_height*0.6):
                        text_offset_x = 5  # pixels to skip after box
                        text_width = 400   # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[(x,y)] = [text, fill_ratio]
                    else:
                        text_offset_x = 5  # pixels to skip after box
                        text_width = 80    # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[(x,y)] = [text, fill_ratio]

    page_dict["Occurence Dictionary"] = return_dict #returns dictionary of coordinate of the checkbox as keys then the text content and the fill ratio

def get_table():

    """Scans the prisoner table and returns of list of all elements. Needs to be cleaned by prisoner for the final data."""

    roi = processing_functions.get_roi(cv2_image, (50, 1000), (1600, 1400)) 
    text = pytesseract.image_to_string(roi, config='--psm 12')

    cells = []
    stripped_text = text.strip().splitlines()
    prohibited = ["Detainees Involved", "Name", "Date of Birth", "Date Confined", "Arresting Charge", "|"]
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

    page_dict["Table Contents"] = cells

def get_injuries():
    """
    Retrieves recorded injuries
    """

    roi = processing_functions.get_roi(cv2_image, (300, 1380), (1600, 1450))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1200)

    page_dict["Injuries?"] = text

def get_resulting_death():
    """
    Retrieves if there was a death that occured, which may result in all below functions being called.
    """

    roi = processing_functions.get_roi(cv2_image, (350, 1450), (1600, 1530)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.25, adjust_width=50)    

    page_dict["Resulting Death?"] = text

def get_deceased_cause_date_time():
    """
    Retirves name of deceased, caused of death, and the date and time
    """
    roi = processing_functions.get_roi(cv2_image, (100, 1510), (1600, 1700))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Cause, Date, and Time"] = text

def get_suicide_watch():
    """
    Retrieves whether the deceased was on suicide watch
    """
    roi = processing_functions.get_roi(cv2_image, (1000, 1700), (1300, 1780)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=40)

    page_dict["Deceased on Suicide Watch"] = text

def get_reported():
    """
    Retrieves the name of the individual who reported the deceased.
    """
    roi = processing_functions.get_roi(cv2_image, (100, 1750), (1600, 1820))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Reporter"] = text

def get_deceased_examined():
    """
    Returns whether the deceased was examined by a doctor and if so, when
    """
    roi = processing_functions.get_roi(cv2_image, (640, 1820), (1600, 1880))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1200)

    page_dict["Deceased Examined by Physician"] = text

def get_deceased_illness():
    """
    Returns whether the deceased displayed signs of illness.
    """
    roi = processing_functions.get_roi(cv2_image, (640, 1820), (1600, 1880))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=800)
    if text != "No":
        new_roi = processing_functions.get_roi(cv2_image, (100,1940), (1600,2000))
        follow_up_text = processing_functions.basic_text_line(new_roi)
        text += follow_up_text

    page_dict["Deceased Signs of Illness"] = text

def main():
    get_facility_type()
    get_facility_name()
    get_facility_phone()
    get_address()
    get_date()
    get_time()
    get_am_pm()
    get_occurence_dict()
    get_table()
    get_injuries()
    get_resulting_death()
    if page_dict["Resulting Death?"] == "Yes":
        get_deceased_cause_date_time()
        get_suicide_watch()
        get_reported()
        get_deceased_examined()
        get_deceased_illness()
    print (page_dict)

if __name__ == "__main__":
    main()