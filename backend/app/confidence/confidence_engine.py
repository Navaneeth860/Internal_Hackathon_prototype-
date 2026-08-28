import logging
from typing import List
from backend.app.extraction.schemas import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)

class ConfidenceEngine:
    """
    ConfidenceEngine calculates field-level heuristic confidence scores
    combining OCR confidence, extraction quality, and validation warnings.
    
    CRITICAL: These scores are heuristic prototype confidence estimates. 
    They are NOT statistically calibrated probabilities.
    """
    
    def __init__(self):
        pass

    def calculate(self, extraction_result: ExtractionResult) -> ExtractionResult:
        """
        Computes the confidence score and updates explanation for each field.
        """
        for field in extraction_result.fields:
            self._score_field(field)
            
        return extraction_result

    def _score_field(self, field: ExtractedField) -> None:
        """
        Heuristic scoring logic for a single field.
        """
        # 1. Base Score from OCR Confidence
        if not field.source_elements:
            field.confidence = 0.0
            field.explanation = "Field is missing or not detected in OCR output."
            return
            
        avg_ocr_conf = sum(el.confidence for el in field.source_elements) / len(field.source_elements)
        score = avg_ocr_conf
        
        # 2. Adjust based on Extraction Quality (Heuristics)
        extraction_type_penalty = 1.0
        details = []
        
        if "directly" in (field.explanation or ""):
            details.append("extracted directly via inline pattern match")
        elif "spatial" in (field.explanation or "") or "neighbor" in (field.explanation or ""):
            # Spatial layouts are slightly less deterministic than inline matches
            extraction_type_penalty = 0.92
            score *= extraction_type_penalty
            details.append("extracted via geometric/spatial proximity heuristics")
            
        # 3. Validation Warnings Deductions
        validation_penalty = 0.0
        has_db_conflict = False
        has_format_warning = False
        
        for warning in field.validation_warnings:
            if "Conflict" in warning:
                has_db_conflict = True
                validation_penalty += 0.25  # Big deduction for database registry mismatch
            elif "Format" in warning:
                has_format_warning = True
                validation_penalty += 0.15  # Deduction for format warning
            elif "Required" in warning:
                validation_penalty += 0.20  # Deduction for missing required field
                
        score = max(0.0, score - validation_penalty)
        
        # 4. Final status classification
        if field.status == "UNCERTAIN":
            score = min(score, 0.50)  # Cap uncertain fields at 50%
            
        # Clamp between 0.0 and 1.0
        final_score = round(max(0.0, min(1.0, score)), 2)
        field.confidence = final_score
        
        # 5. Build Human-Readable Explainability text
        status_percent = int(final_score * 100)
        expl_parts = [
            f"Heuristic confidence is estimated at {status_percent}%.",
            f"OCR character confidence is {int(avg_ocr_conf * 100)}% based on character recognition quality."
        ]
        
        if details:
            expl_parts.append(f"Value was {' and '.join(details)}.")
            
        if has_db_conflict:
            expl_parts.append("CRITICAL: Field value conflicts with registered government mock registry records.")
        elif has_format_warning:
            expl_parts.append("WARNING: Field does not conform to expected formatting standards.")
            
        # Explicit disclaimer
        expl_parts.append(
            "Note: This score is a prototype heuristic estimate based on OCR quality, extraction reliability, "
            "and validation signals; it is not a calibrated statistical probability."
        )
        
        field.explanation = " ".join(expl_parts)
