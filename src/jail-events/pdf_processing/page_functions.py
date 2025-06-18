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

"""
TO DO
link sip 
"""

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

page_dict = {"Deceased Cause, Date, and Time": "N/A",
             "Deceased on Suicide Watch": "N/A",
             "Deceased Reporter": "N/A",
             "Deceased Examined by Physician": "N/A",
             "Deceased Signs of Illness": "N/A"
} #initializing dictionary without conditional values at first

pdf_path = Path(__file__).resolve().parents[2] / "jail-events" / "data" / "jails-data" / "samples" / "FOIA - December 2024 UO Part 1P58.pdf"

doc = pdf2image.convert_from_path(pdf_path, dpi=300) #creates list object 

pil_image = doc[0]
cv2_image = np.array(pil_image)

cv2_image = cv2.cvtColor(np.array(cv2_image), cv2.COLOR_RGB2BGR)

def get_facility_type():
    """
    Retrieves first three letters of facility type, to be processed later
    """
    #x1 = .5176, y1= .15, x2 = .7647, y2 = .2181
    roi = processing_functions.get_roi(cv2_image, (1320, 395), (1950, 720)) #what do we need to do again once we have the box?
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=80)

    page_dict["Facility Type"] = text

def get_facility_name():
    """
    Retrieves full name of the facility
    """
    #x1 = .1588, y1= .25, x2 = .6471, y2 = .2955
    roi = processing_functions.get_roi(cv2_image, (405, 825), (1650, 975))
    text = processing_functions.basic_text_line(roi)

    page_dict["Facility Name"] = text

def get_facility_phone():
    """
    Retrieves phone number to contact the facility
    """
    #x1 = .7529, y1= .25, x2 = .8823, y2 = .2955
    roi = processing_functions.get_roi(cv2_image, (1920, 825), (2250, 975))
    text = processing_functions.basic_text_line(roi)

    page_dict["Phone Number"] = text

def get_address():
    """
    Retrieves street address for facility.
    """
    #x1 = .1235, y1= .3, x2 = .8823, y2 = .3181
    roi = processing_functions.get_roi(cv2_image, (315, 990), (2250, 1050))
    text = processing_functions.basic_text_line(roi)

    page_dict["Address"] = text

def get_date():
    """Retrieves date of incident. """
    #x1 = .2, y1= .3318, x2 = .4941, y2 = .3636
    roi = processing_functions.get_roi(cv2_image, (510, 1095), (1260, 1200))
    text = processing_functions.basic_text_line(roi)

    page_dict["Date"] = text

def get_time():
    """
    Retrieves the raw tine of the incident. May be in either military or standard time.
    """
    #x1 = .2, y1= .3318, x2 = .4941, y2 = .3636
    roi = processing_functions.get_roi(cv2_image, (1650, 1095), (2100, 1200))
    text = processing_functions.basic_text_line(roi)

    page_dict["Time of Day"] = text

def get_am_pm():
    """
    For incidents not in military time, retrieves whether they occured in the AM or PM
    """
    #x1 = .8235, y1= .3318, x2 = .9706, y2 = .3636
    roi = processing_functions.get_roi(cv2_image, (2100, 1095), (2475, 1200)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.3, adjust_width=100)

    page_dict["AM or PM"] = text

def get_occurence_dict(): #need to edit this down
    """
    Creates a dictionary of every possible occurence, text if applicable, and the fill ratio of its box for comparison.
    """
    #x1 = .2, y1= .375, x2 = .9706, y2 = .4545

    type_start_point = (510, 1238)
    type_end_point = (2475, 1500)

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
                        text_offset_x = 15  # pixels to skip after box
                        text_width = 600   # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[(x,y)] = [text, fill_ratio]
                    else:
                        text_offset_x = 15  # pixels to skip after box
                        text_width = 120    # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                        return_dict[(x,y)] = [text, fill_ratio]

    page_dict["Occurence Dictionary"] = return_dict #returns dictionary of coordinate of the checkbox as keys then the text content and the fill ratio

def get_table():

    """Scans the prisoner table and returns of list of all elements. Needs to be cleaned by prisoner for the final data."""
    #x1 = .0294, y1= .4545, x2 = .9412, y2 = .6363

    roi = processing_functions.get_roi(cv2_image, (75, 1500), (2400, 2100)) 
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, config='--psm 12')

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

    page_dict["Table Contents"] = cells

def get_injuries():
    """
    Retrieves recorded injuries
    """
    #x1 = .1765, y1= .6272, x2 = .9412, y2 = .6591

    roi = processing_functions.get_roi(cv2_image, (450, 2070), (2400, 2175))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

    page_dict["Injuries?"] = text

def get_resulting_death():
    """
    Retrieves if there was a death that occured, which may result in all below functions being called.
    """
    #x1 = .2059, y1= .6591, x2 = .9412, y2 = .6954

    roi = processing_functions.get_roi(cv2_image, (525, 2175), (2400, 2295)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.25, adjust_width=75)    

    page_dict["Resulting Death?"] = text

def get_deceased_cause_date_time():
    """
    Retirves name of deceased, caused of death, and the date and time
    """
    #x1 = .8235, y1= .3318, x2 = .9706, y2 = .3636

    roi = processing_functions.get_roi(cv2_image, (150, 2265), (2400, 2550))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Cause, Date, and Time"] = text

def get_suicide_watch():
    """
    Retrieves whether the deceased was on suicide watch
    """
    #x1 = .5882, y1= .7727, x2 = .7647, y2 = .8091

    roi = processing_functions.get_roi(cv2_image, (1500, 2550), (1950, 2670)) 
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=60)

    page_dict["Deceased on Suicide Watch"] = text

def get_reported():
    """
    Retrieves the name of the individual who reported the deceased.
    """
    #x1 = .0588, y1= .7955, x2 = .7272, y2 = .8272
    roi = processing_functions.get_roi(cv2_image, (150, 2625), (2400, 2730))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Reporter"] = text

def get_deceased_examined():
    """
    Returns whether the deceased was examined by a doctor and if so, when
    """
    #x1 = .3765, y1= .8272, x2 = .9412, y2 = .8545
    roi = processing_functions.get_roi(cv2_image, (960, 2730), (2400, 2820))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1800)

    page_dict["Deceased Examined by Physician"] = text

def get_deceased_illness():
    """
    Returns whether the deceased displayed signs of illness.
    """
    #x1 = .3765, y1= .8273, x2 = .9412, y2 = .8545
    roi = processing_functions.get_roi(cv2_image, (960, 2730), (2400, 2820))
    contours = processing_functions.blur_edge_contours(roi)
    text = processing_functions.yes_no_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=1200)
    if text != "No":
        new_roi = processing_functions.get_roi(cv2_image, (150,2910), (2400,3000))
        follow_up_text = processing_functions.basic_text_line(new_roi)
        text += follow_up_text

    page_dict["Deceased Signs of Illness"] = text

def main():#need to add image_path 
    #cv2_image = Image.open(image_path) to be done at end - may need to add this as input to other functions?
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