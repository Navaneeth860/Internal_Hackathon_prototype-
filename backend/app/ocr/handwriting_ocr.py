import os
# Disable oneDNN/MKLDNN to prevent runtime compilation crashes on CPU
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import logging
from backend.app.ocr.ocr_models import OCRResult, OCRElement
from typing import List

logger = logging.getLogger(__name__)

# PP-OCRv5 lazy singleton
_hw_ocr_instance = None

def get_handwriting_ocr_engine():
    """
    Lazy-initializes PaddleOCR with PP-OCRv5 models.
    PP-OCRv5 was trained on a mixed corpus including handwritten English text.
    Models: PP-OCRv5_server_det + en_PP-OCRv5_mobile_rec
    """
    global _hw_ocr_instance
    if _hw_ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            logger.info(
                "Initializing handwriting OCR engine "
                "(PP-OCRv5_server_det + en_PP-OCRv5_mobile_rec) -- "
                "models will be downloaded on first run if not cached."
            )
            _hw_ocr_instance = PaddleOCR(
                text_detection_model_name="PP-OCRv5_server_det",
                text_recognition_model_name="en_PP-OCRv5_mobile_rec",
                use_textline_orientation=True,
                enable_mkldnn=False,
            )
            logger.info("Handwriting OCR engine (PP-OCRv5) initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize handwriting OCR engine: {e}")
            raise
    return _hw_ocr_instance


class HandwritingOCREngine:
    """
    Wraps PaddleOCR v5 for handwritten land-record documents.
    Produces the same OCRResult schema as PaddleOCREngine so all downstream
    extraction, validation, confidence, and verification code is unchanged.
    """

    def process(self, image_path: str) -> OCRResult:
        """
        Runs PP-OCRv5 on the given (preprocessed) image.
        Returns an OCRResult with elements, image_width, image_height.
        """
        import cv2
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        height, width = img.shape[:2]

        engine = get_handwriting_ocr_engine()

        try:
            results = engine.ocr(image_path)
        except Exception as e:
            logger.error(f"Handwriting OCR processing error: {e}")
            raise RuntimeError(f"Handwriting OCR engine failed: {e}")

        elements: List[OCRElement] = []

        if results and len(results) > 0:
            first_page = results[0]
            texts  = first_page.get("rec_texts",  [])
            scores = first_page.get("rec_scores", [])
            polys  = first_page.get("rec_polys",  [])

            for i in range(len(texts)):
                text = texts[i]
                conf = float(scores[i])
                poly = polys[i]
                bbox_fmt = [(float(pt[0]), float(pt[1])) for pt in poly]

                elements.append(OCRElement(
                    text=text.strip(),
                    confidence=conf,
                    bbox=bbox_fmt,
                ))

        logger.info(
            f"Handwriting OCR complete. Found {len(elements)} text blocks "
            f"in {os.path.basename(image_path)}."
        )
        return OCRResult(elements=elements, image_width=width, image_height=height)
