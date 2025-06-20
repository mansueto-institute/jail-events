import fitz
import cv2
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple
from PIL import Image
import pytesseract

# From pdf to image with PyMUPDF
def pdf_page_to_image(page: fitz.Page, dpi: int = 300) -> np.ndarray:
    
    """
    Render PDF page to a BGR OPENCV image (Numpy Arry)
    """
    
    #page = pdf_doc[page_num]
    
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
def crop_above_keyword(image: np.ndarray,
                       keyword: str,
                       search_region_fr: float = 0.15,
                       margin= 10, 
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

    h, w = image.shape[:2]
    search_height = int(h* search_region_fr)
    
    # Crop top of image
    top_region = image[:search_height]
    
    pil = Image.fromarray(cv2.cvtColor(top_region, cv2.COLOR_BGR2RGB))
    config = f"--oem {oem} --psm {psm} -l {lang}"
    data = pytesseract.image_to_data(pil, config=config, output_type=pytesseract.Output.DICT)
    
    tops = []
    list_keywords = keyword.split()
    for i, text in enumerate(data["text"]):
        if text and any(kw.lower() in text.lower() for kw in list_keywords):
            tops.append(data["top"][i])
    if not tops:
        # keyword not found: no crop
        return image
    
    top_pixel_in_region = min(tops)
    actual_crop_line = max(0, top_pixel_in_region - margin)
    print(f"Found '{keyword}' at y={top_pixel_in_region} in search region")
    print(f"Cropping above y={actual_crop_line} in full image")

    return image[actual_crop_line:]


# Function to remove it
def remove_header_footer(image: np.ndarray,
                         header_frac: float = 0.15,
                         footer_frac: int = 712) -> np.ndarray:
    """
    Crop out a fixed fraction of the top and bottom of the image,
    to drop headers & footers that confuse auto-crop.
    
    Args:
      image        – BGR or gray image
      header_frac  – fraction of height to remove from top (0.15 = 15%)
      footer_frac  – fraction of height to remove from bottom
    Returns:
      Cropped image without header/footer bands.
    """
    
    h, w = image.shape[:2]
    top_cut    = int(h * header_frac)
    bottom_cut = int(h * (1 - footer_frac))
    if top_cut >= bottom_cut:
        print(f"W: Invalid crop coordinates (top={top_cut}, bottom={bottom_cut})")
        return image
    return image[top_cut:bottom_cut, :]

# It need to be strengthed
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
    threshold: int = 250, 
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
    threshold: int = 200,
    margin: int = 30,
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

    # 3: Scale content to fit available space
    scale_x = available_width / crop_width
    scale_y = available_height / crop_height
    scale = min(scale_x, scale_y)
    
    new_width = int(crop_width * scale)
    new_height = int(crop_height * scale)

    if scale != 1.0:
        cropped = cv2.resize(cropped, (new_width, new_height), 
                                   interpolation=cv2.INTER_AREA)
        print(f"Content scaled by {scale:.3f} to fit canvas")
    else:
        print("Content fits without scaling")

    # Step 4: Create canvas and place content
    canvas = np.full((canvas_height, canvas_width, 3), bgcolor, dtype=image.dtype)
    
    canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = cropped
    
    print(f"Content placed at ({x_offset}, {y_offset}) with size {new_width}x{new_height}")
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
        #This disrtos to fill
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

def pre_process_page(page: fitz.Page,
                     dpi: int = 300, aligned: bool = True,
                    title_keyword: str = "ILLINOIS DEPARTMENT"):
    """
    Full clean & standardize pipeline for one PDF page
    Out: a BGR OpenCV image to be saved
    """
    
    # Specs of output
    canvas_size = (2550, 3300)  # Based on 21.59×27.94 cm at 300 DPI
    content_start = (20,50)
    header_frac = 0
    footer_frac = 0
    
    # 1) page to array
    img = pdf_page_to_image(page, dpi)
    print(f"Original size: {img.shape}")
    # 2) deskew
    img = deskew_image(img)
    print(f"Deskewed size: {img.shape}")
    # NEW:
    img = crop_scanner_border(img, border_threshold=140)
    # 3) smart removal of header
    img = crop_above_keyword(
        img, 
        keyword=title_keyword,
        search_region_fr=0.15,  # Search top 15%
        margin=15
    )
    # 4) run again deskew if needed
    #img = deskew_image(img)
    # 4) remove footer
    img = remove_header_footer(img, header_frac=header_frac, footer_frac=footer_frac)

    # Aligned to position if aligned is trye or Centered otherwise
    if aligned:
        # standard with start on specific location
        out_img = extract_and_align_content(
        img,
        threshold=240,        # Adjust based on the PDF background color
        margin=10,            # Space around detected content
        content_offset= content_start,  # Where content will be placed
        canvas_size=canvas_size
        )
    else:
        #Centered
        img = auto_crop_margins(img, threshold=240, margin=10)
        out_img = standardize_canvas(img, target_size=canvas_size)
    
    return out_img