import type { UploadResponse, ExtractionResult } from "../types/api";

const host = window.location.hostname || "localhost";
const BASE_URL = `http://${host}:8000`;

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function processDocument(documentId: string): Promise<ExtractionResult> {
  const res = await fetch(`${BASE_URL}/documents/${documentId}/process`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Processing failed" }));
    throw new Error(err.detail || "Processing failed");
  }

  return res.json();
}

export async function getRecord(recordId: string): Promise<ExtractionResult> {
  const res = await fetch(`${BASE_URL}/records/${recordId}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Record retrieval failed" }));
    throw new Error(err.detail || "Record retrieval failed");
  }

  return res.json();
}

export async function correctField(
  recordId: string,
  fieldName: string,
  correctedValue: string
): Promise<ExtractionResult> {
  const res = await fetch(`${BASE_URL}/records/${recordId}/fields/${fieldName}/correct`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ corrected_value: correctedValue }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Correction failed" }));
    throw new Error(err.detail || "Correction failed");
  }

  return res.json();
}

export async function verifyField(recordId: string, fieldName: string): Promise<ExtractionResult> {
  const res = await fetch(`${BASE_URL}/records/${recordId}/fields/${fieldName}/verify`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Verification failed" }));
    throw new Error(err.detail || "Verification failed");
  }

  return res.json();
}

export async function verifyDocument(recordId: string): Promise<ExtractionResult> {
  const res = await fetch(`${BASE_URL}/records/${recordId}/verify`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Document verification failed" }));
    throw new Error(err.detail || "Document verification failed");
  }

  return res.json();
}

export async function getAuditLogs(recordId: string): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/records/${recordId}/audit-logs`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch audit logs" }));
    throw new Error(err.detail || "Failed to fetch audit logs");
  }

  return res.json();
}

