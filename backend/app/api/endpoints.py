import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import DBDocument, DBRecord, DBAuditLog
from backend.app.pipeline.document_pipeline import DocumentPipeline
from backend.app.pipeline.verification_manager import VerificationManager
from backend.app.extraction.schemas import ExtractionResult
from backend.app.validation.validator import Validator

logger = logging.getLogger(__name__)
router = APIRouter()

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
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        
        # Save document metadata to database
        db_doc = DBDocument(id=document_id, filename=filename, filepath=save_path)
        db.add(db_doc)
        db.commit()
        
        logger.info(f"File uploaded successfully: {filename} saved to {save_path}")
        return {
            "document_id": document_id,
            "filename": filename,
            "status": "UPLOADED"
        }
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

@router.post("/documents/{document_id}/process")
def process_document(document_id: str, db: Session = Depends(get_db)):
    """
    Processes the uploaded document using the existing Phase 1+2 DocumentPipeline.
    Stores and indexes the resulting ExtractionResult in the records database.
    """
    # Fetch file path from database
    db_doc = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not db_doc or not os.path.exists(db_doc.filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
        
    file_path = db_doc.filepath
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
        
        # Link the record directly to the document_id and save
        db_record = db.query(DBRecord).filter(DBRecord.id == document_id).first()
        if db_record:
            db_record.document_type = result.document_type
            db_record.image_url = image_url
            db_record.json_data = result.model_dump_json()
        else:
            db_record = DBRecord(
                id=document_id,
                document_type=result.document_type,
                image_url=image_url,
                json_data=result.model_dump_json()
            )
            db.add(db_record)
        
        db.commit()
        
        logger.info(f"Successfully processed document '{document_id}'. Saved record. Image URL: {image_url}")
        return result
    except Exception as e:
        logger.error(f"Processing failed for document '{document_id}': {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

@router.get("/records/{record_id}")
def get_record(record_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the processed structured record by record ID.
    """
    db_record = db.query(DBRecord).filter(DBRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
    
    # Deserialize string back to ExtractionResult object
    return ExtractionResult.model_validate_json(db_record.json_data)

@router.get("/records/{record_id}/audit-logs")
def get_audit_logs(record_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the audit trail log history for a specific record.
    """
    logs = db.query(DBAuditLog).filter(DBAuditLog.record_id == record_id).order_by(DBAuditLog.timestamp.desc()).all()
    return [
        {
            "id": log.id,
            "record_id": log.record_id,
            "field_name": log.field_name,
            "user_role": log.user_role,
            "action": log.action,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]

@router.post("/records/{record_id}/fields/{field_name}/correct")
def correct_field(record_id: str, field_name: str, payload: CorrectionRequest, db: Session = Depends(get_db)):
    """
    Applies a human correction to a specific field.
    Preserves original_value for auditing.
    """
    db_record = db.query(DBRecord).filter(DBRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    record = ExtractionResult.model_validate_json(db_record.json_data)
    
    # Check if field_name exists in record fields
    field_names = {field.name for field in record.fields}
    if field_name not in field_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{field_name}' not found in record."
        )
        
    # Get current old value
    old_value = None
    for field in record.fields:
        if field.name == field_name:
            old_value = field.value
            break
            
    try:
        manager = VerificationManager()
        updated_record = manager.correct_field(record, field_name, payload.corrected_value)
        
        # Re-run Validator to dynamically compute validation warnings after corrections (e.g. Area logical sums)
        validator = Validator()
        updated_record = validator.validate(updated_record)
        
        # Save back to database
        db_record.json_data = updated_record.model_dump_json()
        
        # Insert audit log
        audit_log = DBAuditLog(
            record_id=record_id,
            field_name=field_name,
            user_role="OPERATOR",
            action="CORRECTED",
            old_value=old_value,
            new_value=payload.corrected_value
        )
        db.add(audit_log)
        
        db.commit()
        return updated_record
    except Exception as e:
        logger.error(f"Field correction failed for record '{record_id}': {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correction failed: {str(e)}"
        )

@router.post("/records/{record_id}/fields/{field_name}/verify")
def verify_field(record_id: str, field_name: str, db: Session = Depends(get_db)):
    """
    Approves the extracted field value as correct/valid.
    """
    db_record = db.query(DBRecord).filter(DBRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    record = ExtractionResult.model_validate_json(db_record.json_data)
    
    field_names = {field.name for field in record.fields}
    if field_name not in field_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{field_name}' not found in record."
        )
        
    # Get current value
    old_value = None
    for field in record.fields:
        if field.name == field_name:
            old_value = field.value
            break
            
    try:
        manager = VerificationManager()
        updated_record = manager.verify_field(record, field_name)
        
        # Save back to database
        db_record.json_data = updated_record.model_dump_json()
        
        # Insert audit log
        audit_log = DBAuditLog(
            record_id=record_id,
            field_name=field_name,
            user_role="REGISTRAR",
            action="VERIFIED",
            old_value=old_value,
            new_value=old_value if old_value else ""
        )
        db.add(audit_log)
        
        db.commit()
        return updated_record
    except Exception as e:
        logger.error(f"Field verification failed for record '{record_id}': {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.post("/records/{record_id}/verify")
def verify_document(record_id: str, db: Session = Depends(get_db)):
    """
    Auto-verifies all remaining unverified fields in the record.
    """
    db_record = db.query(DBRecord).filter(DBRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
        
    record = ExtractionResult.model_validate_json(db_record.json_data)
    
    # Get list of fields that will be verified
    to_verify = []
    for field in record.fields:
        if field.verification_status not in ["VERIFIED", "CORRECTED"]:
            to_verify.append((field.name, field.value))
            
    try:
        manager = VerificationManager()
        updated_record = manager.verify_document(record)
        
        # Save back to database
        db_record.json_data = updated_record.model_dump_json()
        
        # Log audit trails for all bulk-verified fields
        for name, val in to_verify:
            audit_log = DBAuditLog(
                record_id=record_id,
                field_name=name,
                user_role="REGISTRAR",
                action="VERIFIED",
                old_value=val,
                new_value=val if val else ""
            )
            db.add(audit_log)
            
        db.commit()
        return updated_record
    except Exception as e:
        logger.error(f"Document verification failed for record '{record_id}': {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document verification failed: {str(e)}"
        )
