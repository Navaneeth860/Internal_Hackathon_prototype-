import os
import uuid
import shutil
import logging
from typing import Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from backend.app.pipeline.document_pipeline import DocumentPipeline
from backend.app.pipeline.verification_manager import VerificationManager
from backend.app.extraction.schemas import ExtractionResult

logger = logging.getLogger(__name__)
router = APIRouter()

# Temporary in-memory databases (approved for Phase 3)
# DOCUMENTS_DB maps document_id (str) -> file_path (str)
DOCUMENTS_DB: Dict[str, str] = {}
# RECORDS_DB maps record_id (str) -> ExtractionResult
RECORDS_DB: Dict[str, ExtractionResult] = {}

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Request schema for human corrections
class CorrectionRequest(BaseModel):
    corrected_value: str

@router.get("/health")
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "version": "1.0.0"}

@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
def upload_document(file: UploadFile = File(...)):
    """
    Receives a document file, validates its extension, saves it locally under data/uploads/,
    and returns a unique document_id.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported types: PNG, JPG, JPEG, PDF."
        )
        
    document_id = str(uuid.uuid4())
    save_filename = f"{document_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_filename)
    
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        DOCUMENTS_DB[document_id] = save_path
        logger.info(f"File uploaded successfully: {filename} saved to {save_path}")
        return {
            "document_id": document_id,
            "filename": filename,
            "status": "UPLOADED"
        }
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

@router.post("/documents/{document_id}/process")
def process_document(document_id: str):
    """
    Processes the uploaded document using the existing Phase 1+2 DocumentPipeline.
    Stores and indexes the resulting ExtractionResult in the in-memory RECORDS_DB.
    """
    file_path = DOCUMENTS_DB.get(document_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
        
    try:
        pipeline = DocumentPipeline()
        result = pipeline.process_document(file_path)
        
        # Determine the preprocessed image filename and URL
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            processed_filename = f"{document_id}_page1_processed_adaptive.png"
        else:
            processed_filename = f"{document_id}_processed_adaptive{ext}"
        
        image_url = f"/data/processed/{processed_filename}"
        result.image_url = image_url
        
        # Link the record directly to the document_id for easy frontend routing
        record_id = document_id
        RECORDS_DB[record_id] = result
        
        logger.info(f"Successfully processed document '{document_id}'. Saved record '{record_id}'. Image URL: {image_url}")
        return result
    except Exception as e:
        logger.error(f"Processing failed for document '{document_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

@router.get("/records/{record_id}")
def get_record(record_id: str):
    """
    Retrieves the processed structured record by record ID.
    """
    record = RECORDS_DB.get(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
    return record

@router.post("/records/{record_id}/fields/{field_name}/correct")
def correct_field(record_id: str, field_name: str, payload: CorrectionRequest):
    """
    Applies a human correction to a specific field.
    Preserves original_value for auditing.
    """
    record = RECORDS_DB.get(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    # Check if field_name exists in record fields
    field_names = {field.name for field in record.fields}
    if field_name not in field_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{field_name}' not found in record."
        )
        
    try:
        manager = VerificationManager()
        updated_record = manager.correct_field(record, field_name, payload.corrected_value)
        RECORDS_DB[record_id] = updated_record
        return updated_record
    except Exception as e:
        logger.error(f"Field correction failed for record '{record_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correction failed: {str(e)}"
        )

@router.post("/records/{record_id}/fields/{field_name}/verify")
def verify_field(record_id: str, field_name: str):
    """
    Approves the extracted field value as correct/valid.
    """
    record = RECORDS_DB.get(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    field_names = {field.name for field in record.fields}
    if field_name not in field_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{field_name}' not found in record."
        )
        
    try:
        manager = VerificationManager()
        updated_record = manager.verify_field(record, field_name)
        RECORDS_DB[record_id] = updated_record
        return updated_record
    except Exception as e:
        logger.error(f"Field verification failed for record '{record_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.post("/records/{record_id}/verify")
def verify_document(record_id: str):
    """
    Auto-verifies all remaining unverified fields in the record.
    """
    record = RECORDS_DB.get(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    try:
        manager = VerificationManager()
        updated_record = manager.verify_document(record)
        RECORDS_DB[record_id] = updated_record
        return updated_record
    except Exception as e:
        logger.error(f"Document verification failed for record '{record_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document verification failed: {str(e)}"
        )

