from pydantic import BaseModel
from typing import List, Tuple, Optional

class OCRElement(BaseModel):
    """
    Represents a single detected block/line of text from OCR.
    """
    text: str
    confidence: float
    # 4 points representing the corners of the bounding box: [top-left, top-right, bottom-right, bottom-left]
    bbox: List[Tuple[float, float]]
    # Optional 4 points representing the normalized corners (0.0 to 1.0)
    normalized_bbox: Optional[List[Tuple[float, float]]] = None
    # Additive OCR provenance. Existing serialized records remain valid when
    # these values are absent.
    page: Optional[int] = None
    ocr_language: Optional[str] = None
    ocr_model: Optional[str] = None

class OCRResult(BaseModel):
    """
    Contains the collection of all extracted elements for a document.
    """
    elements: List[OCRElement]
    image_width: int
    image_height: int
    detected_language: str = "Unknown"
    ocr_languages: List[str] = []
