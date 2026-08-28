from pydantic import BaseModel
from typing import List, Tuple

class OCRElement(BaseModel):
    """
    Represents a single detected block/line of text from OCR.
    """
    text: str
    confidence: float
    # 4 points representing the corners of the bounding box: [top-left, top-right, bottom-right, bottom-left]
    bbox: List[Tuple[float, float]]

class OCRResult(BaseModel):
    """
    Contains the collection of all extracted elements for a document.
    """
    elements: List[OCRElement]
    image_width: int
    image_height: int
