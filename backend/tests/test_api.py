import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import DBDocument, Base

# Set up in-memory SQLite engine for isolated test executions with StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Construct mock tables on setup
Base.metadata.create_all(bind=test_engine)

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
    
    # Query database to confirm persistence
    db = next(override_get_db())
    db_doc = db.query(DBDocument).filter(DBDocument.id == doc_id).first()
    assert db_doc is not None
    assert db_doc.filename == "test_doc.png"
    
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
    
    # Verify Audit Logs got written (1 record)
    response_logs = client.get(f"/records/{doc_id}/audit-logs")
    assert response_logs.status_code == 200
    logs = response_logs.json()
    assert len(logs) == 1
    assert logs[0]["field_name"] == "owner_name"
    assert logs[0]["user_role"] == "OPERATOR"
    assert logs[0]["action"] == "CORRECTED"
    assert logs[0]["old_value"] == "Ramesh Kumar"
    assert logs[0]["new_value"] == "Ramesh Kumar Verma"

    # Test Subdivision Area Logical Mismatch warning
    # Document A contains survey "124/3" (subdivision of parent "124").
    # The parent registered total area is 2.45 acres (sum of plots 1.0 + 0.8 + 0.65 = 2.45).
    # If we correct Area to "2.50 acres", the validator should append an mismatch warning flag!
    response_area = client.post(
        f"/records/{doc_id}/fields/area/correct",
        json={"corrected_value": "2.50 acres"}
    )
    assert response_area.status_code == 200
    updated_area_rec = response_area.json()
    fields_dict = {f["name"]: f for f in updated_area_rec["fields"]}
    assert fields_dict["area"]["value"] == "2.50 acres"
    assert any("Subdivision plot area mismatch" in w for w in fields_dict["area"]["validation_warnings"])

    # Approve Survey Number field as-is
    response_verify = client.post(f"/records/{doc_id}/fields/survey_number/verify")
    assert response_verify.status_code == 200
    updated_record = response_verify.json()
    fields_dict = {f["name"]: f for f in updated_record["fields"]}
    
    assert fields_dict["survey_number"]["verification_status"] == "VERIFIED"
    assert fields_dict["survey_number"]["verified_at"] is not None

    # Verify Audit Logs now contain 3 records (corrected name, corrected area, verified survey number)
    response_logs2 = client.get(f"/records/{doc_id}/audit-logs")
    assert response_logs2.status_code == 200
    logs2 = response_logs2.json()
    assert len(logs2) == 3
    assert logs2[0]["field_name"] == "survey_number"
    assert logs2[0]["user_role"] == "REGISTRAR"
    assert logs2[0]["action"] == "VERIFIED"
    
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
