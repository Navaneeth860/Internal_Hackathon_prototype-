import os
# Disable oneDNN/MKLDNN to prevent piracy and runtime compilation crashes on CPU
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import cv2
import logging
from typing import Dict, List
from backend.app.ocr.ocr_models import OCRElement, OCRResult

logger = logging.getLogger(__name__)

# Lazy initialization flag
_ocr_instances: Dict[str, object] = {}

def get_ocr_engine(language: str = "en"):
    """
    Lazy-initializes and returns a singleton instance of PaddleOCR
    to avoid initialization overhead when importing modules.
    """
    if language not in _ocr_instances:
        try:
            from paddleocr import PaddleOCR as RealPaddleOCR
            # use_textline_orientation=True replaces deprecated use_angle_cls
            # enable_mkldnn=False bypasses OneDNN crash on Windows CPU
            logger.info("Initializing PaddleOCR engine...")
            _ocr_instances[language] = RealPaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False, 
                lang=language,
                enable_mkldnn=False
            )
            logger.info("PaddleOCR engine initialized successfully for language '%s'.", language)
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise e
    return _ocr_instances[language]

class PaddleOCREngine:
    """
    PaddleOCREngine wraps the PaddleOCR model and processes preprocessed images
    into a structured OCRResult schema.
    """
    
    def __init__(self):
        # The engine will lazy load when process() is called
        pass
        
    def process(self, image_path: str, language: str = "en") -> OCRResult:
        """
        Runs OCR on the given image.
        Returns a structured OCRResult.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")
            
        # Get image dimensions using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image at path: {image_path}")
        height, width, _ = img.shape
        
        # Run OCR
        if language not in {"en", "ka"}:
            raise ValueError(f"Unsupported OCR language '{language}'.")
        engine = get_ocr_engine(language)
        
        try:
            # Do not pass cls=True as it is unsupported in this Paddlex-based predict() wrapper
            results = engine.ocr(image_path)
        except Exception as e:
            logger.error(f"PaddleOCR processing error: {e}")
            raise RuntimeError(f"OCR engine failed to run on image: {e}")
            
        elements: List[OCRElement] = []
        
        # In PaddleOCR v3.7+, the returned page object represents a dict-like OCRResult
        if results and len(results) > 0:
            first_page = results[0]
            texts = first_page.get("rec_texts", [])
            scores = first_page.get("rec_scores", [])
            polys = first_page.get("rec_polys", [])
            
            for i in range(len(texts)):
                text = texts[i]
                conf = scores[i]
                poly = polys[i]
                
                # Convert bbox coordinates to flat tuples (float)
                bbox_formatted = [(float(pt[0]), float(pt[1])) for pt in poly]
                
                elements.append(OCRElement(
                    text=text.strip(),
                    confidence=float(conf),
                    bbox=bbox_formatted,
                    page=1,
                    ocr_language=language,
                    ocr_model=("PP-OCRv6 English" if language == "en" else "ka_PP-OCRv3_mobile_rec")
                ))
                
        logger.info(f"OCR processing completed. Found {len(elements)} text blocks.")
        return OCRResult(
            elements=elements,
            image_width=width,
            image_height=height,
            ocr_languages=[language]
        )
