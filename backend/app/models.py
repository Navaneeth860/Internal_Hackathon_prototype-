import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from backend.app.database import Base

class DBDocument(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)

class DBRecord(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True, index=True)  # Matches document UUID
    document_type = Column(String, default="Land Record")
    image_url = Column(String, nullable=True)
    json_data = Column(Text, nullable=False)  # Stores serialized ExtractionResult JSON

class DBAuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    user_role = Column(String, nullable=False)  # "OPERATOR" or "REGISTRAR"
    action = Column(String, nullable=False)     # "CORRECTED" or "VERIFIED"
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
