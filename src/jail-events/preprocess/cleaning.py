import fitz
import cv2
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# From pdf to image with PyMUPDF
def pdf_page_to_image(pdf_doc: fitz.Document, page_num: int = 0, dpi: int = 200) -> np.ndarray:
    """
    Render PDF page to a BGR OPENCV image (Numpy Arry)
    """
    
    page = pdf_doc[page_num]
    
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
    if not lines: 
        return image
    
    angles = []
    for rho, theta in lines[:,0]:
        angle = (theta * 180 / np.pi) - 90
        if abs(angle) <= limit:
            angles.append(angle)
    
    if not angles:
        return image
    
    # 6) rotate by median angle
    median_angle = np.median(angles)
    (h, w) = image.shape[:2]
    center = (w//2, h//2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


# Resize after projection 


# Crop


# Projection of the pdfs 
def project_pdf():
    pass

def main():
    
    # PDFs folter
    data_folder = Path(__file__).parent.parent / "data/Jail Reports/samples"
    
    # File 
    file = data_folder / "FOIA - December 2024 UO Part 1P51.pdf"
    doc = fitz.open(file)
    image = pdf_page_to_image(doc)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    plt.figure(figsize=(12, 16))
    plt.imshow(image_rgb)


if __name__== "__main__":
    main()
    
