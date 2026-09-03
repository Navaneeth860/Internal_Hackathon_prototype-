import logging
from typing import List
from backend.app.extraction.schemas import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)

class ConfidenceEngine:
    """
    ConfidenceEngine calculates field-level reliability scores by combining
    OCR character confidence, pattern extraction quality, and validation warnings.
    """
    
    def __init__(self):
        pass

    def calculate(self, extraction_result: ExtractionResult) -> ExtractionResult:
        """
        Computes the confidence score and updates explanation for each field.
        """
        for field in extraction_result.fields:
            self._score_field(field, extraction_result.extraction_method, extraction_result.document_subtype)
            
        return extraction_result

    def _score_field(self, field: ExtractedField, extraction_method: str = "keyword", document_subtype: str = "Unknown") -> None:
        """
        Heuristic scoring logic for a single field.
        """
        # 1. Base Score from OCR Confidence or LLM baseline
        if not field.source_elements:
            if extraction_method == "llm" and field.status == "SUCCESS":
                avg_ocr_conf = 1.0
                score = 0.85
            else:
                field.confidence = 0.0
                field.explanation = "Field is missing or not detected in OCR output."
                return
        else:
            avg_ocr_conf = sum(el.confidence for el in field.source_elements) / len(field.source_elements)
            score = avg_ocr_conf
        
        # 2. Adjust based on Extraction Quality (Heuristics)
        #
        # Scoring tiers:
        #   LLM extraction          → no cap/penalty; OCR conf used as-is (or 0.85 baseline)
        #   Keyword, direct match   → capped at 0.80 (OCR conf ≠ semantic confidence)
        #   Keyword, spatial match, generic doc   → capped at 0.80 (no further penalty)
        #   Keyword, spatial/prose, Sale/Partition Deed → 0.80 × 0.75 = 0.60
        #
        # The old separate "if spatial in explanation" block has been removed to prevent
        # double-penalisation (it was already covered by the is_direct branch below).
        details = []
        
        if extraction_method == "llm":
            details.append("semantically inferred via local LLM parsing")
        else:
            # Cap: keyword/pattern extraction cannot claim semantic certainty
            score = min(score, 0.80)
            
            is_direct = "directly" in (field.explanation or "")
            is_spatial = "spatial" in (field.explanation or "") or "neighbor" in (field.explanation or "")
            
            if not is_direct and document_subtype in ["Sale Deed", "Kannada Sale Deed", "Partition Deed"]:
                # Pattern matching on legal prose is inherently less reliable
                score *= 0.75
                details.append("extracted via keyword fallback on legal prose document")
            elif is_spatial:
                details.append("extracted via spatial/proximity pattern heuristics")
            elif is_direct:
                details.append("extracted directly via inline pattern match")
            else:
                details.append("extracted via pattern heuristics")
            
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
        ]
        
        if extraction_method == "llm" and not field.source_elements:
            expl_parts.append("No direct OCR bounding box mapped; baseline semantic confidence applied.")
        else:
            expl_parts.append(f"OCR character confidence is {int(avg_ocr_conf * 100)}% based on character recognition quality.")
            
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
