# backend/app/extraction/schemas.py

from pydantic import BaseModel, model_validator
from typing import Optional, List, Tuple
from backend.app.ocr.ocr_models import OCRElement


class ExtractedField(BaseModel):
    """
    Represents a single extracted field from the land record document.

    value          — the active value (corrected_value if human-corrected, else original_value)
    original_value — immutable; set once at extraction time; never overwritten
    corrected_value— set when an Operator submits a correction
    status         — "SUCCESS" | "MISSING" | "UNCERTAIN" | "NOT_PRESENT"
    verification_status — "UNVERIFIED" | "VERIFIED" | "CORRECTED"
    confidence     — heuristic float 0.0–1.0 (NOT a calibrated probability)
    source_elements— the OCR blocks the value was drawn from (for bbox overlays)
    validation_warnings — list of warning strings from the Validator
    explanation    — human-readable note shown in the audit evidence panel
    """
    name: str
    value: Optional[str] = None
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    status: str  # "SUCCESS" | "MISSING" | "UNCERTAIN" | "NOT_PRESENT"
    verification_status: str = "UNVERIFIED"
    verified_at: Optional[str] = None
    confidence: float = 0.0
    source_elements: List[OCRElement] = []
    validation_warnings: List[str] = []
    explanation: Optional[str] = None

    @model_validator(mode='after')
    def initialize_original_value(self) -> 'ExtractedField':
        """
        Capture original_value on first creation.
        This must only run once — the model_validator runs every time the
        object is constructed, including when Pydantic deserialises it from
        the database JSON blob.  We guard with `is None` so we never
        overwrite a previously stored original_value.
        """
        if self.original_value is None and self.value is not None:
            self.original_value = self.value
        return self


class ExtractionResult(BaseModel):
    """
    Full output of the document processing pipeline.

    fields           — list of extracted fields
    document_type    — always "Land Record" (kept for DB/frontend compatibility)
    document_subtype — the specific type: "Sale Deed" | "Partition Deed" | "Unknown"
                       Set by DocumentClassifier. Used by Validator and frontend.
    extraction_method— "llm" (Phase 2 semantic) | "keyword" (Phase 1 regex fallback)
                       Shown in the audit evidence panel so reviewers know the
                       confidence basis of each extraction.
    image_url        — path to the preprocessed image served by the backend
    """
    fields: List[ExtractedField]

    # ── Backwards-compatible fields ───────────────────────────────────────────
    # document_type is kept as "Land Record" so the existing DBRecord.document_type
    # column and the frontend badge continue to work without a migration.
    document_type: str = "Land Record"

    # ── Phase 2 additions ─────────────────────────────────────────────────────
    # document_subtype is what changes with each new document type we add.
    document_subtype: str = "Unknown"

    # extraction_method tells humans and tests which extraction path was taken.
    extraction_method: str = "keyword"

    # Additive document-level OCR metadata used by the existing review UI.
    detected_language: str = "Unknown"
    ocr_languages: List[str] = []

    image_url: Optional[str] = None
