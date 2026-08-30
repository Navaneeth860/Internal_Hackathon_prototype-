import pytest
from unittest.mock import patch, MagicMock
from backend.app.ocr.ocr_models import OCRResult, OCRElement
from backend.app.extraction.document_classifier import DocumentClassifier
from backend.app.extraction.deed_schemas import DOCUMENT_TYPE_SCHEMAS
from backend.app.extraction.llm_extractor import LLMExtractor
from backend.app.validation.rules import (
    validate_sale_deed,
    validate_partition_deed,
    validate_subdivision_area
)
from backend.app.extraction.schemas import ExtractionResult, ExtractedField
from backend.app.validation.validator import Validator

# Mock helper for creating OCRResult
def make_mock_ocr(text_list):
    elements = [
        OCRElement(
            text=text,
            bbox=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            confidence=0.95
        )
        for text in text_list
    ]
    return OCRResult(elements=elements, image_width=800, image_height=1000)

# --- 1. CLASSIFIER TESTS ---

def test_classifier_heuristics():
    classifier = DocumentClassifier()
    
    # Test Sale Deed keywords match
    sale_ocr = make_mock_ocr([
        "THIS DEED OF SALE is executed at Kurukshetra",
        "between the Vendor Ramesh and Purchaser Suresh",
        "for a total sale consideration of Rs 850000."
    ])
    assert classifier.classify(sale_ocr) == "Sale Deed"
    
    # Test Partition Deed keywords match
    partition_ocr = make_mock_ocr([
        "THIS DEED OF PARTITION is executed",
        "among the co-owners to divide the property",
        "allotted share is registered under Survey 87."
    ])
    assert classifier.classify(partition_ocr) == "Partition Deed"
    
    # Test Unknown keyword fallback
    unknown_ocr = make_mock_ocr([
        "This is some generic land receipt",
        "Tax payment record of municipal corporation."
    ])
    # Should fall back to LLM, but mock/mock connection failure returns Unknown
    assert classifier.classify(unknown_ocr) == "Unknown"

@patch("ollama.Client")
def test_classifier_llm_fallback(mock_client_class):
    mock_client = MagicMock()
    mock_client.list.return_value = {}
    mock_client_class.return_value = mock_client
    
    classifier = DocumentClassifier()
    unknown_ocr = make_mock_ocr(["Generic text"])
    
    # Mock LLM returns Sale Deed classification
    mock_client.generate.return_value = {"response": "This is a Sale Deed document."}
    assert classifier.classify(unknown_ocr) == "Sale Deed"
    
    # Mock LLM returns Partition Deed classification
    mock_client.generate.return_value = {"response": "Classification: Partition Deed"}
    assert classifier.classify(unknown_ocr) == "Partition Deed"
    
    # Mock LLM returns random text
    mock_client.generate.return_value = {"response": "Not clear, Unknown"}
    assert classifier.classify(unknown_ocr) == "Unknown"

# --- 2. SCHEMAS TESTS ---

def test_deed_schemas():
    assert "Sale Deed" in DOCUMENT_TYPE_SCHEMAS
    assert "Partition Deed" in DOCUMENT_TYPE_SCHEMAS
    
    sale_fields = {f["name"] for f in DOCUMENT_TYPE_SCHEMAS["Sale Deed"]}
    assert "seller_name" in sale_fields
    assert "buyer_name" in sale_fields
    assert "sale_consideration" in sale_fields
    assert "document_date" in sale_fields
    
    partition_fields = {f["name"] for f in DOCUMENT_TYPE_SCHEMAS["Partition Deed"]}
    assert "parties" in partition_fields
    assert "party_count" in partition_fields
    assert "share_allocation" in partition_fields

# --- 3. LLM EXTRACTOR TESTS ---

@patch("backend.app.extraction.llm_extractor.ollama.Client")
def test_llm_extractor_success(mock_client_class):
    mock_client = MagicMock()
    mock_client.list.return_value = {}
    mock_client.generate.return_value = {
        "response": (
            "Here is the result:\n"
            "```json\n"
            "{\n"
            '  "document_date": "15-06-2025",\n'
            '  "seller_name": "Ramesh Kumar",\n'
            '  "buyer_name": "Suresh Kumar",\n'
            '  "sale_consideration": "Rs. 8,50,000",\n'
            '  "survey_number": "124/3",\n'
            '  "area": "2.45 Acres",\n'
            '  "property_location": "Rampur",\n'
            '  "village": "Rampur",\n'
            '  "district": "Kurukshetra",\n'
            '  "registration_details": "543/2025",\n'
            '  "seller_address": "Rampur",\n'
            '  "buyer_address": "Kurukshetra"\n'
            "}\n"
            "```"
        )
    }
    mock_client_class.return_value = mock_client
    extractor = LLMExtractor()
    ocr = make_mock_ocr(["Ramesh sells to Suresh for 850000 on 15-06-2025 in Rampur"])
    
    res = extractor.extract(ocr, "Sale Deed")
    assert res is not None
    assert res.document_subtype == "Sale Deed"
    assert res.extraction_method == "llm"
    
    fields_map = {f.name: f for f in res.fields}
    assert fields_map["seller_name"].value == "Ramesh Kumar"
    assert fields_map["buyer_name"].value == "Suresh Kumar"
    assert fields_map["sale_consideration"].value == "Rs. 8,50,000"
    assert fields_map["seller_name"].status == "SUCCESS"

@patch("backend.app.extraction.llm_extractor.ollama.Client")
def test_llm_extractor_uncertain_null(mock_client_class):
    mock_client = MagicMock()
    mock_client.list.return_value = {}
    mock_client.generate.return_value = {
        "response": (
            "{\n"
            '  "document_date": "UNCERTAIN",\n'
            '  "seller_name": null,\n'
            '  "buyer_name": "Suresh"\n'
            "}"
        )
    }
    mock_client_class.return_value = mock_client
    extractor = LLMExtractor()
    ocr = make_mock_ocr(["Ambiguous deed"])
    
    res = extractor.extract(ocr, "Sale Deed")
    assert res is not None
    fields_map = {f.name: f for f in res.fields}
    assert fields_map["document_date"].status == "UNCERTAIN"
    assert fields_map["seller_name"].status == "NOT_PRESENT"
    assert fields_map["buyer_name"].value == "Suresh"

@patch("backend.app.extraction.llm_extractor.ollama.Client")
def test_llm_extractor_malformed_json_fallback(mock_client_class):
    mock_client = MagicMock()
    mock_client.list.return_value = {}
    mock_client.generate.return_value = {
        "response": "This is not json: Ramesh bought from Suresh."
    }
    mock_client_class.return_value = mock_client
    extractor = LLMExtractor()
    ocr = make_mock_ocr(["Bad JSON format"])
    
    # Parsing malformed JSON must return None to trigger keyword fallback
    assert extractor.extract(ocr, "Sale Deed") is None

# --- 4. VALIDATION TESTS ---

def test_sale_deed_validation_rules():
    # 1. Valid Sale Deed (no warnings)
    warns = validate_sale_deed("Ramesh Kumar", "Suresh Kumar", "15-06-2025", "Rs. 8,50,000")
    assert len(warns) == 0
    
    # 2. Seller identical to buyer
    warns = validate_sale_deed("Ramesh Kumar", "Ramesh Kumar", "15-06-2025", "Rs. 8,50,000")
    assert len(warns) == 1
    assert "identical" in warns[0]
    
    # 3. Invalid date format
    warns = validate_sale_deed("Ramesh Kumar", "Suresh Kumar", "June 2025", "Rs. 8,50,000")
    assert len(warns) == 1
    assert "date" in warns[0]
    
    # 4. Invalid consideration amount
    warns = validate_sale_deed("Ramesh Kumar", "Suresh Kumar", "15-06-2025", "None/Free")
    assert len(warns) == 1
    assert "consideration" in warns[0]

def test_partition_deed_validation_rules():
    # 1. Valid Partition Deed
    warns = validate_partition_deed("Ramesh, Suresh, Priya", "3", "3.10", "1.05 + 1.05 + 1.00")
    assert len(warns) == 0
    
    # 2. Insufficient parties count
    warns = validate_partition_deed("Ramesh Kumar", "1", "3.10", "3.10")
    assert len(warns) == 1
    assert "at least two" in warns[0]
    
    # 3. Party count mismatch list length
    warns = validate_partition_deed("Ramesh, Suresh", "3", "3.10", "1.55 + 1.55")
    assert len(warns) == 1
    assert "count" in warns[0]
    
    # 4. Allocated shares sum mismatch
    warns = validate_partition_deed("Ramesh, Suresh", "2", "3.10 acres", "Ramesh: 1.50, Suresh: 1.50")
    assert len(warns) == 1
    assert "match" in warns[0]

def test_validator_clears_old_warnings():
    validator = Validator()
    field = ExtractedField(
        name="owner_name",
        value="Ramesh Kumar",
        status="SUCCESS",
        validation_warnings=["Stale Warning Conflict"]
    )
    result = ExtractionResult(fields=[field], document_subtype="Unknown")
    
    # Ingesting clean record should clear the stale warning
    res = validator.validate(result)
    assert len(res.fields[0].validation_warnings) == 0


# --- 5. FIELD EXTRACTOR SCHEMA SELECTION TESTS ---

def test_field_extractor_uses_sale_deed_schema_when_subtype_given():
    """
    When subtype='Sale Deed', the field extractor must use the 12-field Sale Deed schema,
    NOT the generic 8-field land record schema that contains owner_name.
    
    This is the regression test for the bug where keyword fallback ignored subtype
    and always used the generic schema, producing 'owner_name' garbage output.
    """
    from backend.app.extraction.field_extractor import FieldExtractor
    
    extractor = FieldExtractor()
    
    # OCR text that looks like a Sale Deed but doesn't have Ollama available
    sale_deed_ocr = make_mock_ocr([
        "SALE DEED",
        "This deed is executed on 15-06-2025",
        "Between Ramesh Kumar, vendor, resident of Rampur",
        "And Suresh Kumar, purchaser, resident of Bengaluru Rural",
        "Survey Number: 124/3",
        "Area: 2.45 Acres",
        "Village: Rampur",
    ])
    
    result = extractor.extract(sale_deed_ocr, subtype="Sale Deed")
    field_names = {f.name for f in result.fields}
    
    # Sale Deed schema fields must be present
    assert "seller_name" in field_names, "Sale Deed schema must include seller_name"
    assert "buyer_name" in field_names, "Sale Deed schema must include buyer_name"
    assert "sale_consideration" in field_names, "Sale Deed schema must include sale_consideration"
    assert "registration_details" in field_names, "Sale Deed schema must include registration_details"
    
    # Generic land record fields must NOT appear
    assert "owner_name" not in field_names, (
        "Sale Deed keyword fallback must NOT use generic 'owner_name' field. "
        "Bug: pipeline was calling extract(ocr_result) without subtype."
    )
    assert "khasra_number" not in field_names, "Sale Deed schema must not include khasra_number"
    assert "khata_number" not in field_names, "Sale Deed schema must not include khata_number"


def test_field_extractor_uses_generic_schema_when_no_subtype():
    """When subtype is None/Unknown, the generic 8-field schema is used."""
    from backend.app.extraction.field_extractor import FieldExtractor
    
    extractor = FieldExtractor()
    ocr = make_mock_ocr(["Owner Name: Ramesh Kumar", "Survey No: 124/3"])
    result = extractor.extract(ocr, subtype=None)
    field_names = {f.name for f in result.fields}
    
    assert "owner_name" in field_names
    assert "survey_number" in field_names


def test_keyword_fallback_does_not_return_prose_as_owner_name():
    """
    The keyword extractor must NOT return prose clauses as owner_name.
    'and possessor of the property described below. The' must be rejected.
    """
    from backend.app.extraction.field_extractor import FieldExtractor
    
    extractor = FieldExtractor()
    # OCR text where 'possessor' keyword appears followed by a prose clause
    prose_ocr = make_mock_ocr([
        "the sole owner and possessor of the property described below. The vendor",
    ])
    
    result = extractor.extract(prose_ocr, subtype=None)
    owner_field = next((f for f in result.fields if f.name == "owner_name"), None)
    assert owner_field is not None
    
    if owner_field.value is not None:
        # Value must not start with prepositions or contain prose clause markers
        value = owner_field.value.lower()
        prepositions = {"of", "and", "the", "for", "by", "with", "in", "on", "at"}
        first_word = value.split()[0] if value.split() else ""
        assert first_word not in prepositions, (
            f"owner_name must not start with a preposition. Got: '{owner_field.value}'"
        )
        assert "possessor" not in value, f"owner_name must not contain 'possessor'. Got: '{owner_field.value}'"
        assert "described below" not in value, f"Prose clause leaked into owner_name: '{owner_field.value}'"


# --- 6. CONFIDENCE TESTS ---

def test_keyword_extracted_field_confidence_below_100():
    """
    A keyword-extracted field must never have 100% confidence even when
    OCR character recognition is perfect (0.99 or 1.0).
    
    100% confidence implies semantic certainty. Keyword/pattern extraction
    does not provide that guarantee.
    """
    from backend.app.confidence.confidence_engine import ConfidenceEngine
    from backend.app.ocr.ocr_models import OCRElement
    
    # Simulate a field extracted via keyword with perfect OCR confidence
    perfect_ocr_el = OCRElement(
        text="Ramesh Kumar",
        bbox=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        confidence=1.0   # perfect OCR
    )
    
    field = ExtractedField(
        name="owner_name",
        value="Ramesh Kumar",
        status="SUCCESS",
        source_elements=[perfect_ocr_el],
        explanation="Extracted directly from line: 'Owner Name: Ramesh Kumar' via regex."
    )
    
    result = ExtractionResult(
        fields=[field],
        extraction_method="keyword",
        document_subtype="Unknown"
    )
    
    engine = ConfidenceEngine()
    scored = engine.calculate(result)
    
    assert scored.fields[0].confidence < 1.0, (
        f"Keyword-extracted field must not have 100% confidence. "
        f"Got: {scored.fields[0].confidence * 100:.0f}%. "
        "OCR character confidence ≠ semantic extraction confidence."
    )
    # Should be capped at 0.80 before other deductions
    assert scored.fields[0].confidence <= 0.80


def test_sale_deed_keyword_fallback_confidence_penalized():
    """
    On a Sale Deed, keyword fallback should apply the prose-document penalty,
    resulting in confidence significantly below 0.80.
    """
    from backend.app.confidence.confidence_engine import ConfidenceEngine
    from backend.app.ocr.ocr_models import OCRElement
    
    el = OCRElement(
        text="Ramesh Kumar",
        bbox=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        confidence=0.99
    )
    
    # Simulate a spatial neighbor extraction (not "directly")
    field = ExtractedField(
        name="seller_name",
        value="Ramesh Kumar",
        status="SUCCESS",
        source_elements=[el],
        explanation="Extracted spatial neighbor: 'Ramesh Kumar' aligned with keyword 'vendor'."
    )
    
    result = ExtractionResult(
        fields=[field],
        extraction_method="keyword",
        document_subtype="Sale Deed"
    )
    
    engine = ConfidenceEngine()
    scored = engine.calculate(result)
    
    # With 0.80 cap × 0.75 prose penalty × 0.92 spatial penalty ≈ 0.552
    assert scored.fields[0].confidence < 0.75, (
        f"Sale Deed keyword fallback on spatial extraction should have low confidence. "
        f"Got: {scored.fields[0].confidence}"
    )
