"""Regression coverage for Karnataka Kannada Sale Deed support.

Fixtures use fictional OCR output so tests do not require a binary document or
downloaded OCR model.
"""

from backend.app.confidence.confidence_engine import ConfidenceEngine
from backend.app.extraction.document_classifier import DocumentClassifier
from backend.app.extraction.field_extractor import FieldExtractor
from backend.app.ocr.language_detection import detect_language
from backend.app.ocr.ocr_models import OCRElement, OCRResult
from backend.app.validation.validator import Validator


def make_ocr(lines):
    elements = []
    for index, (text, language) in enumerate(lines):
        elements.append(
            OCRElement(
                text=text,
                confidence=0.94,
                bbox=[(10.0, index * 30.0), (500.0, index * 30.0), (500.0, index * 30.0 + 20), (10.0, index * 30.0 + 20)],
                page=1,
                ocr_language=language,
                ocr_model="fixture",
            )
        )
    return OCRResult(elements=elements, image_width=800, image_height=1000, ocr_languages=["en", "ka"])


KANNADA_SALE_LINES = [
    ("ಮಾರಾಟ ಪತ್ರ", "ka"),
    ("ಮಾರಾಟಗಾರ: ರಮೇಶ್ ಕುಮಾರ್", "ka"),
    ("ಖರೀದಿದಾರ: Priya Rao", "ka"),
    ("ದಿನಾಂಕ: 15-06-2025", "ka"),
    ("ಮಾರಾಟದ ಮೊತ್ತ: ರೂ. 8,50,000", "ka"),
    ("ಸರ್ವೇ ಸಂಖ್ಯೆ: 124/3", "ka"),
    ("ಹಿಸ್ಸಾ ಸಂಖ್ಯೆ: 3", "ka"),
    ("ಖಾತೆ ಸಂಖ್ಯೆ: 456", "ka"),
    ("ವಿಸ್ತೀರ್ಣ: 2.45 ಎಕರೆ", "ka"),
    ("ಗ್ರಾಮ: ರಾಮಪುರ", "ka"),
    ("ಹೋಬಳಿ: ಉದಾಹರಣೆ ಹೋಬಳಿ", "ka"),
    ("ತಾಲ್ಲೂಕು: ಬೆಂಗಳೂರು ದಕ್ಷಿಣ", "ka"),
    ("ಜಿಲ್ಲೆ: ಬೆಂಗಳೂರು ನಗರ", "ka"),
    ("ಚೆಕ್ ಸಂಖ್ಯೆ: 123456", "ka"),
    ("ಬ್ಯಾಂಕ್: Example Bank", "en"),
    ("ಅಡಮಾನ: ಇಲ್ಲ", "ka"),
]


def test_script_ratio_detects_mixed_kannada_and_english():
    ocr = make_ocr(KANNADA_SALE_LINES)
    assert detect_language(ocr.elements) == "Mixed Kannada + English"


def test_classifier_distinguishes_kannada_sale_and_existing_english_types():
    classifier = DocumentClassifier()
    assert classifier.classify(make_ocr(KANNADA_SALE_LINES)) == "Kannada Sale Deed"
    english_sale = make_ocr([("SALE DEED Vendor Purchaser sale consideration", "en")])
    english_partition = make_ocr([("PARTITION DEED co-owners allotted share divide", "en")])
    assert classifier.classify(english_sale) == "Sale Deed"
    assert classifier.classify(english_partition) == "Partition Deed"


def test_kannada_sale_extraction_preserves_unicode_fields_and_provenance():
    result = FieldExtractor().extract(make_ocr(KANNADA_SALE_LINES), subtype="Kannada Sale Deed")
    fields = {field.name: field for field in result.fields}

    assert fields["seller_name"].value == "ರಮೇಶ್ ಕುಮಾರ್"
    assert fields["buyer_name"].value == "Priya Rao"
    assert fields["sale_consideration"].value == "ರೂ. 8,50,000"
    assert fields["survey_number"].value == "124/3"
    assert fields["hissa_number"].value == "3"
    assert fields["khata_number"].value == "456"
    assert fields["area"].value == "2.45 ಎಕರೆ"
    assert fields["village"].value == "ರಾಮಪುರ"
    assert fields["hobli"].value == "ಉದಾಹರಣೆ ಹೋಬಳಿ"
    assert fields["taluk"].value == "ಬೆಂಗಳೂರು ದಕ್ಷಿಣ"
    assert fields["district"].value == "ಬೆಂಗಳೂರು ನಗರ"
    assert fields["cheque_number"].value == "123456"
    assert fields["bank_name"].value == "Example Bank"
    assert fields["encumbrance_status"].value == "ಇಲ್ಲ"
    assert fields["survey_number"].original_value == "124/3"
    assert fields["survey_number"].source_elements[0].ocr_language == "ka"


def test_kannada_sale_validation_and_confidence_are_additive():
    result = FieldExtractor().extract(make_ocr(KANNADA_SALE_LINES), subtype="Kannada Sale Deed")
    result.document_subtype = "Kannada Sale Deed"
    result.detected_language = "Mixed Kannada + English"
    result = Validator().validate(result)
    result = ConfidenceEngine().calculate(result)
    fields = {field.name: field for field in result.fields}

    assert not any("Area field" in warning for warning in fields["area"].validation_warnings)
    assert fields["hissa_number"].validation_warnings == []
    assert 0 < fields["seller_name"].confidence < 1
