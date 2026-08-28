# Intelligent Land Record Digitalisation & Validation System

This repository contains the prototype for the **Intelligent Land Record Digitalisation and Validation System (SIH 2026 - Problem SIH26018)**.

The system automates the processing of scanned land record documents through a pipeline of Preprocessing -> OCR -> Field Extraction -> Validation -> Confidence Engine -> Bounding Box Coordinate Normalization -> Human-in-the-Loop Verification.

---

## 1. Setup & Installation

### Prerequisites
* **Python 3.12** (specifically activated in the virtual environment for PaddleOCR/OpenCV binary compatibility on Windows).

### Environment Setup
Create a virtual environment and install all dependencies:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (CMD):
.venv\Scripts\activate.bat

# Install pinned dependencies
pip install -r backend/requirements.txt
```

---

## 2. Generating Mock Documents

Before running test suites, you can programmatically generate four distinct mock documents (A: Clean, B: Noisy/Faded, C: Missing Required Fields, D: Conflict Database Record) simulating different scanning errors:
```bash
python data/generate_test_docs.py
```
This saves synthetic PNG files under `data/samples/`.

---

## 3. Running the Test Suite

Execute the complete backend test suite (Phase 1 core pipeline, Phase 2 human verification logic, Phase 3 FastAPI TestClient endpoints):
```bash
python -m pytest backend/tests/
```

---

## 4. Running the FastAPI Backend Server

Start the local development API server using Uvicorn:
```bash
# From the root directory of the workspace:
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will initialize and bind to `http://127.0.0.1:8000`. You can access the interactive API docs at `http://127.0.0.1:8000/docs`.

### API Endpoint Schema
* **GET** `/health` — Server health status check.
* **POST** `/documents/upload` — Receives file (PNG, JPG, JPEG, PDF), saves it to `data/uploads/`, and returns a unique `document_id`.
* **POST** `/documents/{document_id}/process` — Processes the file using the pipeline and returns the structured `ExtractionResult`.
* **GET** `/records/{record_id}` — Retrieves the structured record.
* **POST** `/records/{record_id}/fields/{field_name}/correct` — Applies a user-edited corrected value while maintaining original OCR values for auditing.
* **POST** `/records/{record_id}/fields/{field_name}/verify` — Approves an extracted value as-is.
* **POST** `/records/{record_id}/verify` — Bulk-approves all remaining unverified fields in the record.
