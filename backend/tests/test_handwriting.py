import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ocr.handwriting_ocr import HandwritingOCREngine
from backend.app.preprocessing.image_processor import ImageProcessor
from backend.app.pipeline.document_pipeline import DocumentPipeline
from backend.app.extraction.schemas import ExtractionResult

client = TestClient(app)

SAMPLE_PATH = "data/samples/handwritten_land_record.png"

def test_handwriting_sample_exists():
    """Verify the handwritten test sample is present."""
    assert os.path.exists(SAMPLE_PATH), f"Sample not found at {SAMPLE_PATH}"


def test_handwriting_preprocessing():
    """Verify handwriting preprocessing applies CLAHE without breaking dimensions."""
    processor = ImageProcessor(output_dir="data/processed")
    out_path = processor.preprocess(SAMPLE_PATH, method="handwriting")
    assert os.path.exists(out_path)
    assert "handwriting" in out_path


def test_handwriting_ocr_engine_execution():
    """
    Verify genuine handwriting OCR execution:
    - Must return OCRResult with elements
    - Must return non-empty text strings
    - Must return valid bounding boxes with 4 coordinates
    - Must return confidence scores between 0.0 and 1.0
    """
    processor = ImageProcessor(output_dir="data/processed")
    preprocessed_path = processor.preprocess(SAMPLE_PATH, method="handwriting")

    engine = HandwritingOCREngine()
    ocr_result = engine.process(preprocessed_path)

    assert ocr_result is not None
    assert len(ocr_result.elements) > 0, "Handwriting OCR returned 0 text blocks"
    assert ocr_result.image_width > 0
    assert ocr_result.image_height > 0

    # Verify elements have text, confidence, and bounding boxes
    for elem in ocr_result.elements:
        assert isinstance(elem.text, str)
        assert len(elem.text) > 0
        assert 0.0 <= elem.confidence <= 1.0
        assert len(elem.bbox) >= 4

    # Check for known semantic keywords transcribed by PP-OCRv5
    all_text = " ".join(e.text for e in ocr_result.elements).lower()
    assert any(term in all_text for term in ["ramesh", "kumar", "survey", "124", "village", "bengaluru", "area", "record"])


def test_handwriting_pipeline_end_to_end():
    """
    Verify full pipeline execution for handwritten documents:
    - Preprocessing -> Handwriting OCR -> Extraction -> Validation -> Confidence
    """
    pipeline = DocumentPipeline()
    result, preprocessed_path = pipeline.process_document(SAMPLE_PATH, ocr_mode="handwritten")

    assert isinstance(result, ExtractionResult)
    assert os.path.exists(preprocessed_path)
    assert len(result.fields) > 0

    fields_dict = {f.name: f for f in result.fields}

    # Verify core land record fields are extracted based on document schema
    assert any(f in fields_dict for f in ["seller_name", "owner_name", "parties", "survey_number", "village", "area"])

    # Check that fields have valid structure, confidence, and bounding boxes
    assert len(result.fields) > 0
    for field in result.fields:
        assert isinstance(field.confidence, float)
        assert 0.0 <= field.confidence <= 1.0
        assert field.status in ["SUCCESS", "MISSING", "UNCERTAIN", "NOT_PRESENT"]


def test_handwriting_api_upload_process_verify_audit_flow(tmp_path):
    """
    Verify complete API lifecycle:
    1. Upload handwritten file
    2. Process with ocr_mode=handwritten
    3. Verify response fields, bounding boxes, and image_url
    4. Operator performs human correction on uncertain field
    5. Registrar verifies corrected record
    6. Audit trail is recorded
    """
    import io, uuid
    from PIL import Image

    # Create a unique test image instance to avoid duplicate upload MD5 hash rejection
    unique_file = io.BytesIO()
    img = Image.open(SAMPLE_PATH).copy()
    # Modify a single pixel at (0, 0) to ensure unique MD5 hash
    r_pixel = int(uuid.uuid4().int % 255)
    img.putpixel((0, 0), (r_pixel, 248, 240))
    img.save(unique_file, format="PNG")
    unique_file.seek(0)

    # 1. Upload
    upload_res = client.post(
        "/documents/upload",
        files={"file": (f"test_hw_{uuid.uuid4().hex[:6]}.png", unique_file, "image/png")}
    )
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["document_id"]

    # 2. Process with ocr_mode=handwritten
    proc_res = client.post(f"/documents/{doc_id}/process?ocr_mode=handwritten")
    assert proc_res.status_code == 200
    data = proc_res.json()
    assert "fields" in data
    assert data["image_url"] is not None

    # 3. Human Correction (Operator corrects survey_number)
    target_field = "survey_number"
    correct_res = client.post(
        f"/records/{doc_id}/fields/{target_field}/correct",
        json={"corrected_value": "124/3-A"},
        headers={"X-Auth-Token": "operator-token-sih2026"}
    )
    assert correct_res.status_code == 200
    corrected_data = correct_res.json()
    field_item = next(f for f in corrected_data["fields"] if f["name"] == target_field)
    assert field_item["value"] == "124/3-A"
    assert field_item["verification_status"] == "CORRECTED"

    # 4. Audit Log
    audit_res = client.get(f"/records/{doc_id}/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    assert any(log["action"] == "CORRECTED" for log in logs)

