import io
from typing import Optional, Dict
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

class OCRProcessor:
    """
    Handles robust extraction of text from scanned PDFs or pure image files 
    using local Tesseract binaries.
    """
    def __init__(self):
        # On Windows, you might need to point explicitly to the tesseract executable if not in PATH.
        # e.g., pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass

    def is_image(self, file_content: bytes, filename: str) -> bool:
        """Heuristic check to see if the file is an image natively."""
        lower_name = filename.lower()
        if lower_name.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            return True
        # Simple magic byte check for images
        if file_content.startswith(b'\xff\xd8') or file_content.startswith(b'\x89PNG'):
            return True
        return False

    def process_image(self, image_content: bytes) -> Dict[int, str]:
        """Extract text from a raw image file."""
        try:
            image = Image.open(io.BytesIO(image_content))
            text = pytesseract.image_to_string(image)
            return {1: text.strip()}
        except Exception as e:
            print(f"OCR Image Processing Error: {str(e)}")
            raise

    def process_pdf(self, pdf_bytes: bytes) -> Dict[int, str]:
        """Convert a scanned PDF into images and extract all text natively."""
        try:
            # Requires poppler installed on the host system.
            images = convert_from_bytes(pdf_bytes, dpi=300)
            pages_dict = {}

            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                pages_dict[i + 1] = page_text.strip()

            return pages_dict
        except Exception as e:
            print(f"OCR PDF Processing Error: {str(e)}")
            raise

    def process(self, file_content: bytes, filename: str) -> Dict[int, str]:
        """Main entrypoint: detect filetype and route to appropriate OCR logic."""
        if self.is_image(file_content, filename):
            return self.process_image(file_content)
        else:
            # Assume PDF if not explicitly an image
            return self.process_pdf(file_content)

ocr_service = OCRProcessor()
