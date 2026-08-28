from pydantic import BaseModel
from typing import Optional, List, Tuple
from backend.app.ocr.ocr_models import OCRElement

class ExtractedField(BaseModel):
    """
    ExtractedField represents a single field extracted from the land record,
    along with its metadata, evidence, and validation.
    """
    name: str  # e.g., "owner_name", "survey_number", "area", etc.
    value: Optional[str] = None  # Extracted text value, normalized where appropriate
    status: str  # Status: "SUCCESS", "MISSING", "UNCERTAIN", "NOT_PRESENT"
    confidence: float = 0.0  # Combined heuristic confidence (0.0 to 1.0)
    source_elements: List[OCRElement] = []  # The OCR source text blocks and coordinates
    validation_warnings: List[str] = []  # Specific validation failures or warnings
    explanation: Optional[str] = None  # Readable reasoning for confidence or issues

class ExtractionResult(BaseModel):
    """
    Aggregated extraction output for the document.
    """
    fields: List[ExtractedField]
    document_type: str = "Land Record"
