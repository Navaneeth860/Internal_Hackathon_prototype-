import os
import logging
from typing import List, Optional, Tuple

from backend.app.preprocessing.image_processor import ImageProcessor
from backend.app.ocr.paddle_ocr import PaddleOCREngine
from backend.app.ocr.tesseract_ocr import TesseractOCREngine
from backend.app.extraction.field_extractor import FieldExtractor
from backend.app.explainability.evidence_mapper import EvidenceMapper
from backend.app.validation.validator import Validator
from backend.app.confidence.confidence_engine import ConfidenceEngine
from backend.app.extraction.schemas import ExtractionResult
from backend.app.extraction.document_classifier import DocumentClassifier
from backend.app.extraction.llm_extractor import LLMExtractor
from backend.app.ocr.language_detection import detect_language, has_meaningful_kannada
from backend.app.ocr.ocr_models import OCRElement, OCRResult

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class DocumentPipeline:
    """
    DocumentPipeline orchestrates the entire intelligence process:
    Preprocessing -> OCR -> Classification -> Semantic/LLM Extraction (fallback to Keyword) -> Validation -> Confidence.
    """
    
    def __init__(self, output_dir: str = "data/processed"):
        self.image_processor = ImageProcessor(output_dir=output_dir)
        self.ocr_engine = PaddleOCREngine()
        self.field_extractor = FieldExtractor()
        self.evidence_mapper = EvidenceMapper()
        self.validator = Validator()
        self.confidence_engine = ConfidenceEngine()
        self.classifier = DocumentClassifier()
        self.llm_extractor = LLMExtractor()

    @staticmethod
    def _needs_kannada_probe(result: OCRResult) -> bool:
        """Avoid a second OCR pass for clearly readable English documents."""
        text = " ".join(element.text for element in result.elements)
        english_legal_markers = ("deed", "sale", "partition", "survey", "owner", "village")
        avg_confidence = (
            sum(element.confidence for element in result.elements) / len(result.elements)
            if result.elements else 0.0
        )
        return (
            detect_language(result.elements) != "English"
            or avg_confidence < 0.72
            or not any(marker in text.lower() for marker in english_legal_markers)
        )

    @staticmethod
    def _bbox_center(element: OCRElement) -> Tuple[float, float]:
        return (
            sum(point[0] for point in element.bbox) / len(element.bbox),
            sum(point[1] for point in element.bbox) / len(element.bbox),
        )

    def _merge_kannada_and_english(self, english: OCRResult, kannada: OCRResult) -> OCRResult:
        """Choose Kannada text for Kannada lines and English text for other lines."""
        selected: List[OCRElement] = list(english.elements)
        for kannada_element in kannada.elements:
            if not has_meaningful_kannada([kannada_element]):
                continue
            kx, ky = self._bbox_center(kannada_element)
            nearest_index = None
            nearest_distance = float("inf")
            for index, english_element in enumerate(selected):
                ex, ey = self._bbox_center(english_element)
                distance = abs(kx - ex) + abs(ky - ey)
                if distance < nearest_distance:
                    nearest_index, nearest_distance = index, distance
            if nearest_index is not None and nearest_distance < 45:
                selected[nearest_index] = kannada_element
            else:
                selected.append(kannada_element)

        selected.sort(key=lambda element: (min(point[1] for point in element.bbox), min(point[0] for point in element.bbox)))
        return OCRResult(
            elements=selected,
            image_width=english.image_width,
            image_height=english.image_height,
            detected_language=detect_language(selected),
            ocr_languages=["en", "ka"],
        )

    def process_document(
        self,
        file_path: str,
        preprocess_method: str = "adaptive",
        ocr_mode: str = "printed",
        ocr_language: str = "auto",
    ) -> Tuple[ExtractionResult, str]:
        """
        Runs the end-to-end processing pipeline on a land-record document.
        Supported inputs: PNG, JPG, JPEG, PDF.

        Args:
            file_path        : Path to the uploaded document.
            preprocess_method: OpenCV preprocessing method. Defaults to 'adaptive' for
                               printed docs; automatically overridden to 'handwriting'
                               when ocr_mode='handwritten'.
            ocr_mode         : 'printed' (default) — PP-OCRv6, adaptive preprocessing.
                               'handwritten'         — PP-OCRv5, CLAHE preprocessing.

        Returns:
            Tuple of (ExtractionResult, preprocessed_image_path).
            The preprocessed_image_path is the actual file saved to disk — use it
            to build the correct web-accessible image_url.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")
        if ocr_language not in {"auto", "en", "ka"}:
            raise ValueError("ocr_language must be 'auto', 'en', or 'ka'.")

        # Route preprocessing method based on ocr_mode
        if ocr_mode == "handwritten" and preprocess_method == "adaptive":
            preprocess_method = "handwriting"
        elif ocr_language == "ka" and preprocess_method == "adaptive":
            # Adaptive binarisation can erase Kannada vowel marks and joined
            # glyphs. Preserve the original printed strokes for the Kannada
            # recognizer in the demo route.
            preprocess_method = "grayscale"

        file_ext = os.path.splitext(file_path)[1].lower()
        target_image_path = file_path
        
        # 1. Gracefully handle PDF files — render ALL pages and stitch vertically
        if file_ext == ".pdf":
            logger.info("PDF document detected. Rendering all pages via PyMuPDF...")
            try:
                import pymupdf as fitz
                import numpy as np
                import cv2 as _cv2

                pdf_image_dir = "data/processed/pdf_pages"
                os.makedirs(pdf_image_dir, exist_ok=True)

                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    raise ValueError("PDF file contains no pages.")

                # 300 DPI improves recognition of dense Kannada legal text and
                # its combining vowel marks. PyMuPDF uses 72 DPI as its base.
                mat = fitz.Matrix(4.17, 4.17)
                page_arrays = []

                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    # Convert PyMuPDF pixmap to numpy BGR array for OpenCV
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, pix.n
                    )
                    # PyMuPDF returns RGB — convert to BGR for OpenCV
                    img_bgr = _cv2.cvtColor(img_array, _cv2.COLOR_RGB2BGR)
                    page_arrays.append(img_bgr)
                    logger.info(f"  Rendered page {page_num + 1}/{doc.page_count} ({pix.width}×{pix.height}px)")

                doc.close()

                # Stitch pages vertically with a 20px grey separator between each
                if len(page_arrays) == 1:
                    stitched = page_arrays[0]
                else:
                    max_width = max(arr.shape[1] for arr in page_arrays)
                    separator = np.full((20, max_width, 3), 180, dtype=np.uint8)  # light grey bar

                    padded = []
                    for arr in page_arrays:
                        if arr.shape[1] < max_width:
                            # Pad narrower pages with white on the right
                            pad = np.full((arr.shape[0], max_width - arr.shape[1], 3), 255, dtype=np.uint8)
                            arr = np.concatenate([arr, pad], axis=1)
                        padded.append(arr)

                    interleaved = []
                    for i, arr in enumerate(padded):
                        interleaved.append(arr)
                        if i < len(padded) - 1:
                            interleaved.append(separator)

                    stitched = np.concatenate(interleaved, axis=0)

                pdf_base = os.path.splitext(os.path.basename(file_path))[0]
                stitched_filename = f"{pdf_base}_all_pages.png"
                target_image_path = os.path.join(pdf_image_dir, stitched_filename)
                _cv2.imwrite(target_image_path, stitched)
                logger.info(
                    f"Stitched {len(page_arrays)} page(s) into: {target_image_path} "
                    f"({stitched.shape[1]}×{stitched.shape[0]}px)"
                )

            except ImportError as ie:
                raise RuntimeError(f"PDF processing failed: {ie}. Run: pip install pymupdf")
            except Exception as e:
                logger.error(f"Error converting PDF to image: {e}")
                raise RuntimeError(f"Failed to process PDF file: {e}")

        # 2. Image Preprocessing (OpenCV)
        logger.info(f"Step 1/5: Preprocessing document with method: '{preprocess_method}'...")
        preprocessed_path = self.image_processor.preprocess(target_image_path, method=preprocess_method)

        # 3. OCR — run PaddleOCR (English) first for document classification;
        #         if Kannada is detected, re-run with Tesseract (kan+eng LSTM)
        logger.info("Step 2/5: Extracting text via PaddleOCR (English probe)...")
        english_result = self.ocr_engine.process(preprocessed_path, language="en")
        english_result.detected_language = detect_language(english_result.elements)
        ocr_result = english_result

        # Quick classification on English OCR to check if it's a Kannada document
        quick_subtype = self.classifier.classify(english_result)
        logger.info("Quick classifier result on English OCR: '%s'", quick_subtype)

        is_kannada_doc = (
            ocr_language == "ka"
            or quick_subtype == "Kannada Sale Deed"
            or self._needs_kannada_probe(english_result)
        )

        if is_kannada_doc:
            logger.info(
                "Step 2b/5: Kannada document detected. "
                "Switching to Tesseract LSTM (kan+eng) for accurate Kannada OCR..."
            )
            tess_engine = TesseractOCREngine()
            ocr_result = tess_engine.process(preprocessed_path)
            ocr_result.detected_language = "Kannada"
            logger.info(
                "Tesseract OCR complete. %d tokens extracted.", len(ocr_result.elements)
            )

        # Classification on the best OCR result
        if ocr_language == "ka" or quick_subtype == "Kannada Sale Deed":
            subtype = "Kannada Sale Deed"
            logger.info("Document subtype set to: 'Kannada Sale Deed'")
        else:
            logger.info("Classifying document subtype...")
            subtype = self.classifier.classify(ocr_result)
        logger.info(f"Document classified as: '{subtype}'")


        # 4. Field Extraction
        extraction_result = None
        # The local LLM is not allowed to infer Kannada values without direct
        # OCR evidence; deterministic extraction returns missing fields rather
        # than plausible-looking fabricated values.
        if subtype in ["Sale Deed", "Partition Deed"]:
            logger.info(f"Step 3/5: Attempting LLM semantic extraction for subtype '{subtype}'...")
            extraction_result = self.llm_extractor.extract(ocr_result, subtype)
            
        if extraction_result is None:
            logger.info(f"Step 3/5: Using keyword/pattern extractor (fallback) with subtype='{subtype}'...")
            extraction_result = self.field_extractor.extract(ocr_result, subtype=subtype)
            extraction_result.document_subtype = subtype
            extraction_result.extraction_method = "keyword"
            
            # Normalize and map coordinates for spatial display
            extraction_result = self.evidence_mapper.map_evidence(
                extraction_result, 
                ocr_result.image_width, 
                ocr_result.image_height
            )
        else:
            logger.info("LLM semantic extraction succeeded.")
            # Map evidence coords to ensure full frontend alignment compatibility
            extraction_result = self.evidence_mapper.map_evidence(
                extraction_result,
                ocr_result.image_width,
                ocr_result.image_height
            )

        extraction_result.detected_language = ocr_result.detected_language
        extraction_result.ocr_languages = ocr_result.ocr_languages

        # 5. Validation (Format & Subtype Checks)
        logger.info("Step 4/5: Running validation and format checkers...")
        validated_result = self.validator.validate(extraction_result)

        # 6. Confidence Scoring (Heuristics Engine)
        logger.info("Step 5/5: Calculating field-level heuristic confidence...")
        final_result = self.confidence_engine.calculate(validated_result)

        logger.info("Pipeline execution completed successfully.")
        # Return both the result AND the actual preprocessed image path so callers
        # can build the correct web-accessible image_url regardless of input format.
        return final_result, preprocessed_path
