"""
TesseractOCREngine — Kannada-optimised OCR using Tesseract 5 LSTM.

Used exclusively for Kannada Sale Deed documents. PaddleOCR's Kannada
model (ka_PP-OCRv3_mobile_rec) produces garbled output for Kannada script;
Tesseract's `kan` LSTM model returns clean Unicode Kannada text.
"""

import os
import logging
from typing import List

import cv2
import pytesseract
from PIL import Image

from backend.app.ocr.ocr_models import OCRElement, OCRResult

logger = logging.getLogger(__name__)

# Point pytesseract at the Windows installation path
_TESS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_TESS_PATH):
    pytesseract.pytesseract.tesseract_cmd = _TESS_PATH


class TesseractOCREngine:
    """
    Wraps Tesseract OCR for Kannada documents.

    Uses `kan+eng` language pair so that English names, numbers, and
    registration tokens embedded in Kannada deeds are also captured.
    Returns an OCRResult compatible with the rest of the pipeline.
    """

    def process(self, image_path: str) -> OCRResult:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to read image: {image_path}")

        height, width = img_bgr.shape[:2]

        # Pre-processing for scanned Kannada legal documents
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(
            enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        pil_img = Image.fromarray(binary)

        # PSM 3: Fully automatic page segmentation; OEM 1: LSTM only
        custom_config = r"--psm 3 --oem 1"

        try:
            data = pytesseract.image_to_data(
                pil_img,
                lang="kan+eng",
                config=custom_config,
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseract executable not found. "
                "Install from https://github.com/UB-Mannheim/tesseract/wiki"
            )

        elements: List[OCRElement] = []
        n = len(data["text"])

        for i in range(n):
            text = data["text"][i].strip()
            if not text:
                continue
            conf_raw = data["conf"][i]
            if conf_raw < 0:
                continue

            confidence = float(conf_raw) / 100.0

            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            bbox = [
                (float(x),     float(y)),
                (float(x + w), float(y)),
                (float(x + w), float(y + h)),
                (float(x),     float(y + h)),
            ]

            elements.append(
                OCRElement(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    page=1,
                    ocr_language="ka",
                    ocr_model="Tesseract-5-LSTM-kan+eng",
                )
            )

        logger.info(
            "TesseractOCREngine: found %d text tokens in '%s'",
            len(elements), image_path,
        )

        return OCRResult(
            elements=elements,
            image_width=width,
            image_height=height,
            ocr_languages=["ka", "en"],
        )
