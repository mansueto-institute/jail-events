import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageEnhance
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

def blur_edge_contours(roi, alpha):
    # cv2.imshow("roi",roi)
    # contrast_img = cv2.convertScaleAbs(roi, alpha=alpha, beta=0.5)
    #contrast_img = np.array(ImageEnhance.Contrast(Image.fromarray(roi)).enhance(2.0))
    # cv2.imshow("ci",contrast_img)
    #blurred_image = cv2.GaussianBlur(contrast_img, (5, 5), 0)
    # cv2.imshow("bi",blurred_image)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    # ERODE to break text up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    eroded = cv2.erode(binary, kernel, iterations=1) #breaking apart text itself

    # (optional) then dilate to re-strengthen box edges
    dilated = cv2.dilate(eroded, kernel, iterations=1)
    #edges = cv2.Canny(roi, 50, 150) #get contoured polygons
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def basic_text_line(roi):
    '''
    Takes simple text image and extracts text.
    '''
    text = None
    text = pytesseract.image_to_string(roi, config='--psm 6')

    return text

def basic_box_check(roi, contours, adjust_fill_ratio, adjust_width, adjust_box_min_box_area): #note to add variable for fill_ratio and text_width?
    '''
    Takes roi and contours, checks if contours are boxes then checks if boxes are filled.
    '''
    text = "None"
    box_list = []
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if contour.ndim == 3:
            contour = contour[:,0]
        carea = ((np.max(contour[:,0]) - np.min(contour[:,0]))) * (np.max(contour[:,1]) - np.min(contour[:,1])) #gets comments from divij
        s = ""
        if (carea > adjust_box_min_box_area) and (carea < 2500):
            s = "**"
        if s == "**":
            x, y, w, h = cv2.boundingRect(approx)
            cropped_rect = roi[y : (y + h), x : (x + w)]
            gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
            margin = int(min(w, h) * 0.1)
            inner = binary[margin:h-margin, margin:w-margin]
            fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
            box_dict = {"x": x, "y": y, "w": w, "h": h, "fill_ratio": fill_ratio, "area": carea}
            box_list.append(box_dict)
    box_list = sorted(box_list, key=lambda d: d["fill_ratio"], reverse=True)
    if len(box_list) < 2:
        return "Error: less than two boxes found"
    max_box = box_list[0]
    min_box = box_list[1]
    if abs (max_box["fill_ratio"] - min_box["fill_ratio"]) > adjust_fill_ratio:
        x = max_box["x"]
        y = max_box["y"]
        w = max_box["w"]
        h = max_box["h"]
        text_offset_x = 10  # pixels to skip after box
        text_width = adjust_width    # width of text region to extract
        if x == 0 or y == 0 or w == 0 or h == 0:
            return "Error creating ROI: zero-length box side"
        text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
        if text_roi.size == 0:
            return "Error creating ROI: text ROI is size 0"
        text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
        _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
        return text
    else: 
        return "No filled box found"


def yes_no_box_check(roi, contours, adjust_fill_ratio, adjust_width):
    text = "No"
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True) #get polgyon curve
        if contour.ndim == 3:
            contour = contour[:,0]
        carea = ((np.max(contour[:,0]) - np.min(contour[:,0]))) * (np.max(contour[:,1]) - np.min(contour[:,1])) #gets comments from divij
        s = ""
        if (carea > 1500) and (carea < 2500):
            s = "**"
        if s == "**":
            x, y, w, h = cv2.boundingRect(approx)
            cropped_rect = roi[y : (y + h), x : (x + w)]
            if cropped_rect.size == 0 or x == 0 or y == 0 or w == 0 or h == 0: #Check for bad parse/proportions
                break
            if w / h > 20 or h / w > 20:
                break
            gray_box = cv2.cvtColor(cropped_rect, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY_INV)
            # Crop inside to ignore border (e.g. 10% margin)
            margin = int(min(w, h) * 0.1)
            inner = binary[margin:h-margin, margin:w-margin]
            fill_ratio = cv2.countNonZero(inner) / float(inner.size) #check how much is filled
            is_filled = fill_ratio > adjust_fill_ratio  # can adjust threashold
            if is_filled:
                text_offset_x = 5  # pixels to skip after box
                text_width = adjust_width    # width of text region to extract
                text_roi = roi[y:y+h, x+w+text_offset_x:x+w+text_offset_x+text_width]
                text_gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
                _, text_thresh = cv2.threshold(text_gray, 150, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(text_thresh, config='--psm 6') #gets first letters of the phrase
                break
    return text
