import os
import logging
from typing import Optional, Tuple

from backend.app.preprocessing.image_processor import ImageProcessor
from backend.app.ocr.paddle_ocr import PaddleOCREngine
from backend.app.extraction.field_extractor import FieldExtractor
from backend.app.explainability.evidence_mapper import EvidenceMapper
from backend.app.validation.validator import Validator
from backend.app.confidence.confidence_engine import ConfidenceEngine
from backend.app.extraction.schemas import ExtractionResult
from backend.app.extraction.document_classifier import DocumentClassifier
from backend.app.extraction.llm_extractor import LLMExtractor

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

    def process_document(
        self,
        file_path: str,
        preprocess_method: str = "adaptive",
        ocr_mode: str = "printed",
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

        # Route preprocessing method based on ocr_mode
        if ocr_mode == "handwritten" and preprocess_method == "adaptive":
            preprocess_method = "handwriting"

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

                mat = fitz.Matrix(2.0, 2.0)  # ~200 DPI
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

        # 3. OCR — route to printed (PP-OCRv6) or handwriting (PP-OCRv5) engine
        if ocr_mode == "handwritten":
            logger.info("Step 2/5: Extracting text via Handwriting OCR engine (PP-OCRv5)...")
            hw_engine = HandwritingOCREngine()
            ocr_result = hw_engine.process(preprocessed_path)
        else:
            logger.info("Step 2/5: Extracting text via Printed OCR engine (PP-OCRv6)...")
            ocr_result = self.ocr_engine.process(preprocessed_path)

        # Document Classification
        logger.info("Classifying document subtype...")
        subtype = self.classifier.classify(ocr_result)
        logger.info(f"Document classified as: '{subtype}'")


        # 4. Field Extraction
        extraction_result = None
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
