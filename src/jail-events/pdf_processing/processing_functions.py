import pytesseract
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt

def get_roi(cv2_image, type_start_point, type_end_point):
    '''
    Takes two diagonal corners of ROI and generates coordinates
    '''
    x1 = min(type_start_point[0], type_end_point[0])
    x2 = max(type_start_point[0], type_end_point[0])
    y1 = min(type_start_point[1], type_end_point[1])
    y2 = max(type_start_point[1], type_end_point[1])

    roi = cv2_image[y1:y2, x1:x2] #initial box for type of facility

    return roi

def basic_text_line(roi):
    '''
    Takes simple text image and extracts text.
    '''
    text = None
    text = pytesseract.image_to_string(roi, config='--psm 6')

    return text

def basic_box_check(roi, contours, adjust_fill_ratio, adjust_width): #note to add variable for fill_ratio and text_width?
    '''
    Takes roi and contours, checks if contours are boxes then checks if boxes are filled.
    '''
    roi_height, roi_width = roi.shape[:2]
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(approx) 
            if 0.85 <= aspect_ratio <= 1.15 and 500 <= area <= 5000: #check if its a box
                if x >= 0 and y >= 0 and x + w <= roi_width and y + h <= roi_height:
                    cropped_rect = roi[y : (y + h), x : (x + w)]
                    gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
                    _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
                    # Crop inside to ignore border (e.g. 10% margin)
                    margin = int(min(w, h) * 0.1)
                    inner = binary[margin:h-margin, margin:w-margin]
                    fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
                    is_filled = fill_ratio > adjust_fill_ratio  # can adjust threashold
                    print(f"Checkbox at ({x},{y}) - Filled: {is_filled}, Fill Ratio: {fill_ratio:.2f}")

                    if is_filled:
                        text_offset_x = 10  # pixels to skip after box
                        text_width = adjust_width    # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase

def yes_no_box_check(roi, contours, adjust_fill_ratio, adjust_width):
    text = "No"
    roi_height, roi_width = roi.shape[:2]
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(approx) 
            if 0.85 <= aspect_ratio <= 1.15 and 500 <= area <= 5000: #check if its a box
                if x >= 0 and y >= 0 and x + w <= roi_width and y + h <= roi_height:
                    cropped_rect = roi[y : (y + h), x : (x + w)]
                    gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
                    _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
                    # Crop inside to ignore border (e.g. 10% margin)
                    margin = int(min(w, h) * 0.1)
                    inner = binary[margin:h-margin, margin:w-margin]
                    fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
                    is_filled = fill_ratio > adjust_fill_ratio  # can adjust threashold
                    print(f"Checkbox at ({x},{y}) - Filled: {is_filled}, Fill Ratio: {fill_ratio:.2f}")
                    if is_filled:
                        if x < roi_width*0.02:
                            text = "No"
                    if is_filled:
                        text_offset_x = 10  # pixels to skip after box
                        text_width = adjust_width    # width of text region to extract
                        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
        return text
