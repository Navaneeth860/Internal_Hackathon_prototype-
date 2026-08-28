import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.endpoints import DOCUMENTS_DB, RECORDS_DB

client = TestClient(app)

def test_health_endpoint():
    """
    Asserts GET /health returns successful status response.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}

def test_upload_endpoints():
    """
    Asserts valid file uploads succeed and invalid formats are rejected.
    """
    # 1. Valid upload (PNG format)
    fake_image = io.BytesIO(b"fake image bytes")
    response = client.post(
        "/documents/upload",
        files={"file": ("test_doc.png", fake_image, "image/png")}
    )
    assert response.status_code == 201
    json_data = response.json()
    assert "document_id" in json_data
    assert json_data["filename"] == "test_doc.png"
    assert json_data["status"] == "UPLOADED"
    
    doc_id = json_data["document_id"]
    assert doc_id in DOCUMENTS_DB
    
    # 2. Reject unsupported file format (.txt)
    fake_txt = io.BytesIO(b"fake text content")
    response_bad = client.post(
        "/documents/upload",
        files={"file": ("test_doc.txt", fake_txt, "text/plain")}
    )
    assert response_bad.status_code == 400
    assert "Unsupported file type" in response_bad.json()["detail"]

def test_process_and_verification_workflow():
    """
    Verifies upload -> process -> correction/verification workflow end-to-end.
    """
    # Upload clean mock Document A
    with open("data/samples/document_a.png", "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("document_a.png", f, "image/png")}
        )
    assert response.status_code == 201
    doc_id = response.json()["document_id"]
    
    # Trigger document pipeline processing
    response_proc = client.post(f"/documents/{doc_id}/process")
    assert response_proc.status_code == 200
    record = response_proc.json()
    assert "fields" in record
    assert "image_url" in record
    assert record["image_url"] == f"/data/processed/{doc_id}_processed_adaptive.png"
    
    fields_dict = {f["name"]: f for f in record["fields"]}
    assert "owner_name" in fields_dict
    assert fields_dict["owner_name"]["value"] == "Ramesh Kumar"
    assert fields_dict["owner_name"]["verification_status"] == "UNVERIFIED"
    assert fields_dict["owner_name"]["original_value"] == "Ramesh Kumar"
    
    # Apply human correction to Owner Name
    response_correct = client.post(
        f"/records/{doc_id}/fields/owner_name/correct",
        json={"corrected_value": "Ramesh Kumar Verma"}
    )
    assert response_correct.status_code == 200
    updated_record = response_correct.json()
    fields_dict = {f["name"]: f for f in updated_record["fields"]}
    
    # Verify provenance preservation
    assert fields_dict["owner_name"]["original_value"] == "Ramesh Kumar"
    assert fields_dict["owner_name"]["corrected_value"] == "Ramesh Kumar Verma"
    assert fields_dict["owner_name"]["value"] == "Ramesh Kumar Verma"
    assert fields_dict["owner_name"]["verification_status"] == "CORRECTED"
    assert fields_dict["owner_name"]["verified_at"] is not None
    
    # Approve Survey Number field as-is
    response_verify = client.post(f"/records/{doc_id}/fields/survey_number/verify")
    assert response_verify.status_code == 200
    updated_record = response_verify.json()
    fields_dict = {f["name"]: f for f in updated_record["fields"]}
    
    assert fields_dict["survey_number"]["verification_status"] == "VERIFIED"
    assert fields_dict["survey_number"]["verified_at"] is not None
    
    # Verify entire document (auto-verifying remaining unverified fields)
    response_verify_doc = client.post(f"/records/{doc_id}/verify")
    assert response_verify_doc.status_code == 200
    final_record = response_verify_doc.json()
    fields_dict = {f["name"]: f for f in final_record["fields"]}
    
    assert fields_dict["owner_name"]["verification_status"] == "CORRECTED"
    assert fields_dict["survey_number"]["verification_status"] == "VERIFIED"
    assert fields_dict["village"]["verification_status"] == "VERIFIED"
    
    # Retrieve the final state of the record via GET
    response_get = client.get(f"/records/{doc_id}")
    assert response_get.status_code == 200
    assert response_get.json() == final_record

