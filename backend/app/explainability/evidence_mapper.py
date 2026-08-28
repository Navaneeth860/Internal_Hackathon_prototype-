import logging
from typing import List, Tuple
from backend.app.extraction.schemas import ExtractionResult
from backend.app.ocr.ocr_models import OCRElement

logger = logging.getLogger(__name__)

class EvidenceMapper:
    """
    EvidenceMapper processes absolute coordinate bounding boxes and maps them
    to normalized percentage coordinates (0.0 to 1.0) for frontend overlays.
    """
    
    def __init__(self):
        pass

    def normalize_bbox(
        self, 
        bbox: List[Tuple[float, float]], 
        width: int, 
        height: int
    ) -> List[Tuple[float, float]]:
        """
        Normalizes a list of (x, y) coordinates relative to the image dimensions.
        Clamps values between 0.0 and 1.0 and rounds to 4 decimal places.
        """
        if width <= 0 or height <= 0:
            logger.warning(f"Invalid image dimensions: {width}x{height}. Skipping normalization.")
            return bbox

        normalized: List[Tuple[float, float]] = []
        for x, y in bbox:
            norm_x = round(max(0.0, min(1.0, x / width)), 4)
            norm_y = round(max(0.0, min(1.0, y / height)), 4)
            normalized.append((norm_x, norm_y))
            
        return normalized

    def map_evidence(
        self, 
        extraction_result: ExtractionResult, 
        image_width: int, 
        image_height: int
    ) -> ExtractionResult:
        """
        Updates the ExtractionResult by calculating and populating 
        normalized_bbox for each OCRElement inside field source_elements.
        """
        if image_width <= 0 or image_height <= 0:
            logger.warning("Invalid image dimensions. Bounding boxes will not be normalized.")
            return extraction_result

        for field in extraction_result.fields:
            for element in field.source_elements:
                element.normalized_bbox = self.normalize_bbox(
                    element.bbox, 
                    image_width, 
                    image_height
                )
                
        logger.info("Successfully normalized evidence bounding boxes for extracted fields.")
        return extraction_result

