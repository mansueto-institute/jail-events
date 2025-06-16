import pytesseract
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt
from utils import processing_functions

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

page_dict = {}

cv2_image = None #Need to add this

contours = None

'''
Assumes we are given the PDF with color and blur applied - should contours be applied first?
'''

def get_facility_type():
    roi = processing_functions.get_roi(cv2_image, (880, 330), (1300, 480)) #what do we need to do again once we have the box?
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.2, adjust_width=50)

    page_dict["Facility Type"] = text

def get_facility_name():
    roi = processing_functions.get_roi(cv2_image, (270, 550), (1100, 650))
    text = processing_functions.basic_text_line(roi)

    page_dict["Facility Name"] = text

def get_facility_phone():
    roi = processing_functions.get_roi(cv2_image, (1280, 550), (1500, 650))
    text = processing_functions.basic_text_line(roi)

    page_dict["Phone Number"] = text

def get_address():
    roi = processing_functions.get_roi(cv2_image, (210, 660), (1500, 700))
    text = processing_functions.basic_text_line(roi)

    page_dict["Address"] = text

def get_date():
    roi = processing_functions.get_roi(cv2_image, (340, 730), (840, 800))
    text = processing_functions.basic_text_line(roi)

    page_dict["Date"] = text

def get_time(): #include both numbers and am/pm here?
    roi = processing_functions.get_roi(cv2_image, (1100, 730), (1400, 800))
    text = processing_functions.basic_text_line(roi)

    page_dict["Time of Day"] = text

def get_am_pm():
    roi = processing_functions.get_roi(cv2_image, (1400, 730), (1650, 800)) 
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=40)

    page_dict["AM or PM"] = text

def get_occurence_dict(): #need to edit this down

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
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(approx) 
            if 0.85 <= aspect_ratio <= 1.15 and 250 <= area <= 5000: #check if its a box
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
    roi = processing_functions.get_roi(cv2_image, (300, 1380), (1600, 1450))
    roi_width = 960
    text = processing_functions.yes_no_box_check(roi, roi_width, contours, adjust_fill_ratio=0.2, adjust_width=1200)

    page_dict["Injuries?"] = text

def get_resulting_death():

    roi = processing_functions.get_roi(cv2_image, (350, 1450), (1600, 1530)) 
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.25, adjust_width=50)    

    page_dict["Resulting Death?"] = text
    #if resulting_death? == "Yes" then run other functions

def get_deceased_cause_date_time():
    roi = processing_functions.get_roi(cv2_image, (100, 1510), (1600, 1700))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Cause, Date, and Time"] = text

def get_suicide_watch():
    roi = processing_functions.get_roi(cv2_image, (1000, 1700), (1300, 1780)) 
    text = processing_functions.basic_box_check(roi, contours, adjust_fill_ratio=0.5, adjust_width=40)

    page_dict["Deceased on Suicide Watch"] = text

def get_reported():
    roi = processing_functions.get_roi(cv2_image, (100, 1750), (1600, 1820))
    text = processing_functions.basic_text_line(roi)

    page_dict["Deceased Reporter"] = text

def get_diseased_examined():
    roi = processing_functions.get_roi(cv2_image, (640, 1820), (1600, 1880))
    roi_width = 960
    text = processing_functions.yes_no_box_check(roi, roi_width, contours, adjust_fill_ratio=0.2, adjust_width=1200)

    page_dict["Deceased Examine by Physician"] = text

def get_diseased_illness():
    roi = processing_functions.get_roi(cv2_image, (640, 1820), (1600, 1880))
    roi_width = 960
    text = processing_functions.yes_no_box_check(roi, roi_width, contours, adjust_fill_ratio=0.2, adjust_width=800)
    if text != "N/A":
        new_roi = processing_functions.get_roi(cv2_image, (100,1940), (1600,2000))
        follow_up_text = processing_functions.basic_text_line(new_roi)
        text += follow_up_text
        
    page_dict["Deceased Signs of Illness"] = text