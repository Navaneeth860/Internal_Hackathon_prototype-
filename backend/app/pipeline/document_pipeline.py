import os
import logging
from typing import Dict, Any, Optional

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

    def process_document(self, file_path: str, preprocess_method: str = "adaptive") -> ExtractionResult:
        """
        Runs the end-to-end processing pipeline on a land-record document.
        Supported inputs: PNG, JPG, JPEG, PDF.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")
            
        file_ext = os.path.splitext(file_path)[1].lower()
        target_image_path = file_path
        
        # 1. Gracefully handle PDF files
        if file_ext == ".pdf":
            logger.info("PDF document detected. Attempting conversion to image...")
            logger.info("PDF document detected. Converting to image via PyMuPDF...")
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path, dpi=200)
                if not pages:
                    raise ValueError("PDF file contains no pages.")
                # Save the first page as a temporary PNG for OCR processing
                import pymupdf as fitz  # PyMuPDF — no Poppler dependency needed
                
                pdf_image_dir = "data/processed/pdf_pages"
                os.makedirs(pdf_image_dir, exist_ok=True)
                pdf_image_name = os.path.splitext(os.path.basename(file_path))[0] + "_page1.png"
                target_image_path = os.path.join(pdf_image_dir, pdf_image_name)
                pages[0].save(target_image_path, "PNG")
                
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    raise ValueError("PDF file contains no pages.")
                
                page = doc[0]  # First page
                # 2x zoom matrix ≈ 200 DPI (default is 72 DPI)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                pix.save(target_image_path)
                doc.close()
                
                logger.info(f"Successfully converted PDF page 1 to: {target_image_path}")
            except ImportError:
                error_msg = (
                    "PDF processing failed: 'pdf2image' package is not installed or 'poppler' is missing from PATH. "
                    "Please install pdf2image and Poppler, or upload direct image formats (PNG, JPG, JPEG)."
                raise RuntimeError(
                    "PDF processing failed: PyMuPDF is not installed. "
                    "Run: pip install pymupdf"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            except Exception as e:
                logger.error(f"Error converting PDF to image: {e}")
                raise RuntimeError(f"Failed to process PDF file: {e}")

        # 2. Image Preprocessing (OpenCV)
        logger.info(f"Step 1/5: Preprocessing document with method: '{preprocess_method}'...")
        preprocessed_path = self.image_processor.preprocess(target_image_path, method=preprocess_method)

        # 3. OCR (PaddleOCR)
        logger.info("Step 2/5: Extracting text & coordinates via PaddleOCR...")
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
        return final_result
