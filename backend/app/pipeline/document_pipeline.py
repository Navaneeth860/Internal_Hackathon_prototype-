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

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class DocumentPipeline:
    """
    DocumentPipeline orchestrates the entire intelligence process:
    Preprocessing -> OCR -> Field Extraction -> Validation -> Confidence.
    """
    
    def __init__(self, output_dir: str = "data/processed"):
        self.image_processor = ImageProcessor(output_dir=output_dir)
        self.ocr_engine = PaddleOCREngine()
        self.field_extractor = FieldExtractor()
        self.evidence_mapper = EvidenceMapper()
        self.validator = Validator()
        self.confidence_engine = ConfidenceEngine()

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
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path, dpi=200)
                if not pages:
                    raise ValueError("PDF file contains no pages.")
                # Save the first page as a temporary PNG for OCR processing
                pdf_image_dir = "data/processed/pdf_pages"
                os.makedirs(pdf_image_dir, exist_ok=True)
                pdf_image_name = os.path.splitext(os.path.basename(file_path))[0] + "_page1.png"
                target_image_path = os.path.join(pdf_image_dir, pdf_image_name)
                pages[0].save(target_image_path, "PNG")
                logger.info(f"Successfully converted PDF page 1 to: {target_image_path}")
            except ImportError:
                error_msg = (
                    "PDF processing failed: 'pdf2image' package is not installed or 'poppler' is missing from PATH. "
                    "Please install pdf2image and Poppler, or upload direct image formats (PNG, JPG, JPEG)."
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

        # 4. Field Extraction (Rule-Based & Spatial Patterns)
        logger.info("Step 3/5: Extracting target land record fields...")
        extraction_result = self.field_extractor.extract(ocr_result)

        # Normalize and map coordinates for explainability
        extraction_result = self.evidence_mapper.map_evidence(
            extraction_result, 
            ocr_result.image_width, 
            ocr_result.image_height
        )

        # 5. Validation (Format & Mock Registry Verification)
        logger.info("Step 4/5: Running validation and format checkers...")
        validated_result = self.validator.validate(extraction_result)

        # 6. Confidence Scoring (Heuristics Engine)
        logger.info("Step 5/5: Calculating field-level heuristic confidence...")
        final_result = self.confidence_engine.calculate(validated_result)

        logger.info("Pipeline execution completed successfully.")
        return final_result
