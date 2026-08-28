from datetime import datetime, timezone
import logging
from backend.app.extraction.schemas import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)

class VerificationManager:
    """
    VerificationManager governs the human-in-the-loop lifecycle.
    It applies user corrections and approvals, records ISO timestamps,
    and preserves original OCR provenance.
    """
    
    def __init__(self):
        pass
        
    def correct_field(self, result: ExtractionResult, field_name: str, new_value: str) -> ExtractionResult:
        """
        Corrects the specified field name with a new human-supplied value.
        Preserves original_value and updates status/timestamps.
        """
        for field in result.fields:
            if field.name == field_name:
                # Store human correction and update active value
                field.corrected_value = new_value
                field.value = new_value
                field.verification_status = "CORRECTED"
                field.verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                
                # When human edits a field, its logical extraction status becomes SUCCESS
                field.status = "SUCCESS" 
                field.explanation = f"Human corrected this field from '{field.original_value}' to '{new_value}'."
                logger.info(f"Field '{field_name}' corrected by human: '{field.original_value}' -> '{new_value}'")
                break
        return result

    def verify_field(self, result: ExtractionResult, field_name: str) -> ExtractionResult:
        """
        Approves the extracted value as correct.
        Updates status and timestamps.
        """
        for field in result.fields:
            if field.name == field_name:
                field.verification_status = "VERIFIED"
                field.verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                logger.info(f"Field '{field_name}' verified by human (value: '{field.value}')")
                break
        return result

    def verify_document(self, result: ExtractionResult) -> ExtractionResult:
        """
        Automatically approves all remaining UNVERIFIED fields in the document.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for field in result.fields:
            if field.verification_status == "UNVERIFIED":
                field.verification_status = "VERIFIED"
                field.verified_at = timestamp
                logger.info(f"Auto-verified field '{field.name}' during document verification.")
        return result
