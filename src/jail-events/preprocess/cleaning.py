import fitz
import cv2
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple
from PIL import Image
import pytesseract
from .crop import resize_image

# From pdf to image with PyMUPDF
def pdf_page_to_image(page: fitz.Page, dpi: int = 300) -> np.ndarray:
    
    """
    Render PDF page to a BGR OPENCV image (Numpy Arry)
    """
    
    # Render page to pix map
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix= mat, alpha = False)
    # Numpy array (RGB)
    img = np.frombuffer(pix.samples, dtype = np.uint8).reshape(pix.height, pix.width, pix.n)
    
    if pix.n == 4: 
        # Drop alpha channel
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else: 
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
    return img

def crop_scanner_border(image: np.ndarray, border_threshold: int = 240) -> np.ndarray:
    """
    Remove grey scanner border and crop to actual document content.
    Assumes document content is brighter than the border.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Find areas BRIGHTER than border (the actual document)
    _, clean_mask = cv2.threshold(gray, border_threshold, 255, cv2.THRESH_BINARY)
    
    # Find the largest white rectangle (the document area)
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Get the largest contour (should be the document)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Crop to the document area with small margin
        margin = 10
        x_start = max(0, x - margin)
        y_start = max(0, y - margin)  
        x_end = min(image.shape[1], x + w + margin)
        y_end = min(image.shape[0], y + h + margin)
        
        return image[y_start:y_end, x_start:x_end]
    
    return image  # If no clean area found, return original

# Get rid off the header & footer
def find_title_y_coordinate(
    image: np.ndarray, 
    keyword: str, 
    margin = 0,
    search_region_frac: float = 0.3) -> int:
    """ Find Y coordiante of ttle keyword"""
    h, w = image.shape[:2]
    search_height = int(h * search_region_frac)
    #Crop image
    top_region = image[:search_height]
    
    pil = Image.fromarray(cv2.cvtColor(top_region, cv2.COLOR_BGR2RGB))
    config = f"--oem 3 --psm 3 -l eng"
    #pil.show()
    data = pytesseract.image_to_data(pil, config=config, output_type=pytesseract.Output.DICT)
    
    # DEBUG: Print what OCR actually sees
    # print(f"DEBUG: OCR detected {len([t for t in data['text'] if t.strip()])} text elements")
    # detected_texts = [text for text in data["text"] if text.strip()]
    # print(f"DEBUG: First 20 detected texts: {detected_texts[:20]}")
    
    tops = []
    list_keywords = keyword.split()
    for i, text in enumerate(data["text"]):
        if text and any(kw.lower() in text.lower() for kw in list_keywords):
            tops.append(data["top"][i])
    if tops:
        return min(tops) - margin
    return None

def crop_above_keyword(image: np.ndarray,
                       keyword: str,
                       search_region_fr: float = 0.3,
                       margin= 5, 
                       oem: int =3,
                       psm: int=3, 
                       lang: str = "eng") -> np.ndarray:
    """
    OCR only the TOP portion of image, find keyword, crop everything above it.
    Much faster than full-page OCR.
    Args:
        image: BGR input image
        keyword: Text to search for (e.g., "JAIL BOOKING REPORT")
        search_region_fr: Fraction of image height to search (0.12 = top 12%)
        margin: Pixels to keep above found keyword
    """
    
    top_pixel_in_region = find_title_y_coordinate(image, keyword, margin,search_region_fr)
    actual_crop_line = max(0, top_pixel_in_region - margin)
    #print(f"Found '{keyword}' at y={top_pixel_in_region} in search region")
    #print(f"Cropping above y={actual_crop_line} in full image")

    return image[actual_crop_line:]

def crop_from_keyword_to_content(image: np.ndarray,
    title_keyword: str = "REPORT EXTRAORDINARY UNUSUAL",
    vertical_content_frac: float = 0.8,
    horizontal_margin: int = 10,
    scan_height: int = 120)-> np.ndarray:
    """
    Cropping content based on title detection:
    """
    h, w = image.shape[:2]
    # 1. Title location
    title_y = find_title_y_coordinate(image, title_keyword)
    
    if title_y is None:
        print(f"Title '{title_keyword}' not found, using fallback crop")
        title_y = int(0.1 * h) # 10% in case not
    
    # 2. Vertical Crop
    y0 = max(0, title_y)
    y1 = min(h, int(y0 + vertical_content_frac*(h-y0)))
    
    vertical_strip = image[y0:y1, :]
    
    # 3. Horizonal boundaries in title area 
    scan_region_height = min(scan_height, vertical_strip.shape[0] //2)
    title_area = vertical_strip[:scan_region_height, :]
    
        # Convert to grayscale and threshold
    gray = cv2.cvtColor(title_area, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 237, 255, cv2.THRESH_BINARY_INV)
    
    # Project onto horizontal axis to find content edges
    h_projection = np.sum(binary, axis=0)
    
    # Find first and last columns with content
    non_zero_cols = np.nonzero(h_projection)[0]
    
    if len(non_zero_cols) > 0:
        left_edge = non_zero_cols[0]
        right_edge = non_zero_cols[-1]

        x0 = max(0, left_edge - horizontal_margin)
        x1 = min(w, right_edge + horizontal_margin)
        
        print(f"With margins: x0={x0}, x1={x1}")
    else:
        print("No horizontal boundaries found, using default margins")
        x0 = int(0.05 * w)
        x1 = int(0.95 * w)
    
    # Step 4: Final horizontal crop
    final_content = vertical_strip[:, x0:x1]
    
    print(f"Final content size: {final_content.shape}")
    return final_content
    

# Deskew the image
def deskew_image(image: np.ndarray, limit: int = 45):
    """
    Detect and correct image skew: Hough line detection
    """
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bw = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV +
                          cv2.THRESH_OTSU)
    edges = cv2.Canny(bw, 50, 150, apertureSize=3)
    
    # Lines 
    lines = cv2.HoughLines(edges, 1, np.pi/ 180, threshold= 200)
    if lines is None: 
        return image
    
    angles = []
    for rho, theta in lines[:,0]:
        angle = (theta * 180 / np.pi) - 90
        if abs(angle) <= limit:
            angles.append(angle)
    
    if not angles:
        return image
    
    median_angle = np.median(angles)
    (h, w) = image.shape[:2]
    center = (w//2, h//2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    deskewed = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )
    return deskewed   
    
def auto_crop_margins(
    image: np.ndarray,
    threshold: int = 180, 
    margin: int = 10) -> np.ndarray:
    """
    Auto-crop any white border on all sides by finding the 
    darkest pixels in the image, then trimming off everything
    outside [top–bottom] × [left–right] plus a small margin.
    Works whether `image` is single-channel or BGR.
    
    Args: 
        image: Input BGR image
        threshold: Grayscale cutoff below which a pixel is 'black'
        margin: Number of extra pixels to keep around detected content
    Returns:
        Cropped image with new top-left aligned to content.
    """
    
    # get gray if needed
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    ys, xs = np.where(gray < threshold)
    if ys.size == 0 or xs.size == 0:
        return image  # nothing dark → no crop

    top    = max(int(ys.min()) - margin,    0)
    left   = max(int(xs.min()) - margin,    0)
    bottom = min(int(ys.max()) + margin, image.shape[0])
    right  = min(int(xs.max()) + margin, image.shape[1])

    return image[top:bottom, left:right]

# Resize after projection

# Cropping and standarization:
def extract_and_align_content(
    image: np.ndarray,
    threshold: int = 180,
    margin: int = 10,
    content_offset: Tuple[int,int] = (20, 20),
    canvas_size: Tuple[int,int] = (1700, 2200),
    bgcolor: Tuple[int,int,int] = (255, 255, 255)
) -> np.ndarray:
    """
    Standarization:
    1) Auto-crop to the darkest pixel box + margin (removes variable margins)
    2) Scale content to fit in available canvas space
    3) Place at fixed offset to ensure consistent positioning
    
    Args:
        image: BGR input image
        threshold: Grayscale cutoff for content detection (200 = very white backgrounds)
        margin: Extra pixels around detected content
        content_offset: (x,y) where top-left of content should be placed
        canvas_size: (width, height) of final standardized image
        bgcolor: Fill color for canvas background
    Returns:
        Fixed-size image with content aligned at consistent position
    """
    # 1: Auto-crop to content boundaries
    cropped = auto_crop_margins(image)

    # 2: Calculate available space on canvas
    canvas_width, canvas_height = canvas_size
    x_offset, y_offset = content_offset
    
    available_width = canvas_width - x_offset
    available_height = canvas_height -y_offset
    
    crop_height, crop_width = cropped.shape[:2]

    # 3: Scale content
    
    scale_x = available_width / crop_width
    scale_y = available_height / crop_height
    scale = min(scale_x, scale_y)
    
    new_width = int(crop_width * scale)
    new_height = int(crop_height * scale)

    cropped = cv2.resize(cropped, (new_width, new_height), 
                                interpolation=cv2.INTER_AREA)

    # Step 4: Create canvas and place content
    canvas = np.full((canvas_height, canvas_width, 3), bgcolor, dtype=image.dtype)
    
    canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = cropped
    return canvas


def standardize_canvas(image: np.ndarray,
                       target_size: tuple = (2550,3300),
                       bg_color: tuple = (255,255,255),
                       allow_upscale: bool = True,
                       preserve_aspect: bool = True) -> np.ndarray:
    """
    Resize the image to fit within `target_size` and then
    pad with bg_color to exactly `target_size`.
    """
    W, H = target_size
    h, w = image.shape[:2]

    if preserve_aspect:
        scale_x = W / w
        scale_y = H / h
        scale = min(scale_x, scale_y)
        if not allow_upscale:
            scale = min(scale, 1.0)
    else: 
        #This distorts to fill available space
        scale_x = W / w
        scale_y = H / h

    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h),
                         interpolation=cv2.INTER_CUBIC if scale>1 else cv2.INTER_AREA)
    # create blank canvas
    canvas = np.full((H, W, 3),
                     bg_color,
                     dtype=np.uint8)
    x_off = (W - new_w) // 2
    y_off = (H - new_h) // 2
    canvas[y_off:y_off+new_h,
           x_off:x_off+new_w] = resized
    return canvas

# New approach using 90% of document croping after detection of title:

def pre_process_page(page: fitz.Page,
                     dpi: int = 300,
                    title_keyword: str = "REPORT EXTRAORDINARY UNUSUAL"):
    """
    Full clean & standardize pipeline for one PDF page
    Out: a BGR OpenCV image to be saved
    """
    
    # Specs of output
    canvas_size = (2550, 3300)  # Based on 21.59×27.94 cm at 300 DPI
    content_start = (20,50)
    
    # 1) page to array
    img = pdf_page_to_image(page, dpi)

    # 2) deskew
    img = deskew_image(img)

    content_roi = crop_above_keyword(
        img, 
        keyword=title_keyword,
        search_region_fr=0.2,
        margin=5
    )
    
    # Aligned to position if aligned is set or Centered otherwise
    #standard with start on specific location
    img = extract_and_align_content(
    content_roi,
    threshold=237,        # Adjust based on the PDF background color
    margin=10,            # Space around detected content
    content_offset= content_start,  # Where content will be placed
    canvas_size=canvas_size
    )
    
    # 3) use the smart crop from statistical analyss
    pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    _, _, cropped_pil = resize_image(pil_image)
    out_img = cv2.cvtColor(np.array(cropped_pil), cv2.COLOR_BAYER_BG2BGR)

    return out_img