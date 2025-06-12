import fitz
import cv2
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# From pdf to image with PyMUPDF
def pdf_page_to_image(pdf_doc: fitz.Document, page_num: int = 0, dpi: int = 200) -> np.ndarray:
    """
    Render PDF page to a BGR OPENCV image (Numpy Arry)
    Args: 
        pdf_doc: Open Fitz.Document object
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
def deskew_image(image: np.ndarray):
    pass


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
    
    plt.figure(figsize=(12, 16))
    plt.imshow(image)


if __name__== "__main__":
    main()
    
