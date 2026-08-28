from pydantic import BaseModel, model_validator
from typing import Optional, List, Tuple
from backend.app.ocr.ocr_models import OCRElement

class ExtractedField(BaseModel):
    """
    ExtractedField represents a single field extracted from the land record,
    along with its metadata, evidence, and validation.
    Supports human-in-the-loop verification and provenance preservation.
    """
    name: str  # e.g., "owner_name", "survey_number", "area", etc.
    value: Optional[str] = None  # Current active value (equals corrected_value if corrected, else original_value)
    original_value: Optional[str] = None  # Immutable value initially extracted by pipeline
    corrected_value: Optional[str] = None  # User-provided corrected value
    status: str  # Status: "SUCCESS", "MISSING", "UNCERTAIN", "NOT_PRESENT"
    verification_status: str = "UNVERIFIED"  # "UNVERIFIED", "VERIFIED", "CORRECTED"
    verified_at: Optional[str] = None  # ISO timestamp of verification/correction
    confidence: float = 0.0  # Combined heuristic confidence (0.0 to 1.0)
    source_elements: List[OCRElement] = []  # The OCR source text blocks and coordinates
    validation_warnings: List[str] = []  # Specific validation failures or warnings
    explanation: Optional[str] = None  # Readable reasoning for confidence or issues

    @model_validator(mode='after')
    def initialize_original_value(self) -> 'ExtractedField':
        """
        Ensures original_value tracks the initial value at creation time.
        """
        if self.original_value is None and self.value is not None:
            self.original_value = self.value
        return self

class ExtractionResult(BaseModel):
    """
    Aggregated extraction output for the document.
    """
    fields: List[ExtractedField]
    document_type: str = "Land Record"
    image_url: Optional[str] = None
