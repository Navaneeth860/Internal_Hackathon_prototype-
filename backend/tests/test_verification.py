import pytest
from datetime import datetime
from backend.app.pipeline.verification_manager import VerificationManager
from backend.app.explainability.evidence_mapper import EvidenceMapper
from backend.app.extraction.schemas import ExtractionResult, ExtractedField
from backend.app.ocr.ocr_models import OCRElement

def test_verification_transitions():
    """
    Test transitions:
      - Default status = UNVERIFIED
      - Human approves existing value -> VERIFIED
      - Human changes value -> CORRECTED
      - Verification timestamp is created
      - original_value is preserved
      - corrected_value is stored
    """
    # Setup mock ExtractionResult (original_value sets automatically to value via validator)
    fields = [
        ExtractedField(name="owner_name", value="Ramesh Kumar", status="SUCCESS"),
        ExtractedField(name="survey_number", value="124/3", status="SUCCESS"),
    ]
    result = ExtractionResult(fields=fields)
    
    # Verify default state
    assert result.fields[0].verification_status == "UNVERIFIED"
    assert result.fields[0].original_value == "Ramesh Kumar"
    assert result.fields[0].corrected_value is None
    assert result.fields[0].verified_at is None
    
    manager = VerificationManager()
    
    # 1. UNVERIFIED -> VERIFIED
    result = manager.verify_field(result, "owner_name")
    assert result.fields[0].verification_status == "VERIFIED"
    assert result.fields[0].original_value == "Ramesh Kumar"
    assert result.fields[0].value == "Ramesh Kumar"
    assert result.fields[0].verified_at is not None
    
    # 2. UNVERIFIED -> CORRECTED
    result = manager.correct_field(result, "survey_number", "124/3A")
    assert result.fields[1].verification_status == "CORRECTED"
    
    # Original value preserved
    assert result.fields[1].original_value == "124/3"
    # Corrected value stored correctly
    assert result.fields[1].corrected_value == "124/3A"
    # Active value is now the corrected value
    assert result.fields[1].value == "124/3A"
    assert result.fields[1].verified_at is not None
    
    # Check timestamp parseability
    dt_str = result.fields[1].verified_at.replace("Z", "")
    dt = datetime.fromisoformat(dt_str)
    assert dt is not None

def test_coordinate_normalization():
    """
    Test that normalized coordinates are in the range 0.0 - 1.0
    and remain traceable to the absolute OCR coordinates.
    """
    # Setup mock OCRElement
    element = OCRElement(
        text="Sample text",
        confidence=0.95,
        bbox=[(100.0, 200.0), (300.0, 200.0), (300.0, 250.0), (100.0, 250.0)]
    )
    fields = [
        ExtractedField(name="owner_name", value="Sample text", status="SUCCESS", source_elements=[element])
    ]
    result = ExtractionResult(fields=fields)
    
    mapper = EvidenceMapper()
    # Image dimensions 800x1000
    result = mapper.map_evidence(result, 800, 1000)
    
    norm_bbox = result.fields[0].source_elements[0].normalized_bbox
    assert norm_bbox is not None
    assert len(norm_bbox) == 4
    
    # Verify all coordinates are in 0.0 - 1.0 range
    for x, y in norm_bbox:
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0
        
    # Check trace coordinates match mathematically
    assert norm_bbox[0] == (0.125, 0.2)   # 100/800 = 0.125, 200/1000 = 0.2
    assert norm_bbox[2] == (0.375, 0.25)  # 300/800 = 0.375, 250/1000 = 0.25

def test_verify_document():
    """
    Test verify_document batch action approves all UNVERIFIED fields 
    while preserving already CORRECTED/VERIFIED ones.
    """
    fields = [
        ExtractedField(name="owner_name", value="Ramesh Kumar", status="SUCCESS"),
        ExtractedField(name="survey_number", value="124/3", status="SUCCESS", verification_status="CORRECTED", corrected_value="124/3A"),
    ]
    result = ExtractionResult(fields=fields)
    manager = VerificationManager()
    
    result = manager.verify_document(result)
    
    # owner_name should become VERIFIED
    assert result.fields[0].verification_status == "VERIFIED"
    # survey_number should remain CORRECTED (not overwritten)
    assert result.fields[1].verification_status == "CORRECTED"

