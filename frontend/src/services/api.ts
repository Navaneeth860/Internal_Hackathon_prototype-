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

export async function processDocument(documentId: string, ocrLanguage: "auto" | "en" | "ka" = "auto"): Promise<ExtractionResult> {
  const params = new URLSearchParams({ ocr_language: ocrLanguage });
  const res = await fetch(`${BASE_URL}/documents/${documentId}/process?${params}`, {
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
  correctedValue: string,
  role: string = "OPERATOR"
): Promise<ExtractionResult> {
  const token = role === "REGISTRAR" ? "registrar-token-sih2026" : "operator-token-sih2026";
  const res = await fetch(`${BASE_URL}/records/${recordId}/fields/${fieldName}/correct`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Auth-Token": token,
    },
    body: JSON.stringify({ corrected_value: correctedValue }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Correction failed" }));
    throw new Error(err.detail || "Correction failed");
  }

  return res.json();
}

export async function verifyField(recordId: string, fieldName: string, role: string = "REGISTRAR"): Promise<ExtractionResult> {
  const token = role === "OPERATOR" ? "operator-token-sih2026" : "registrar-token-sih2026";
  const res = await fetch(`${BASE_URL}/records/${recordId}/fields/${fieldName}/verify`, {
    method: "POST",
    headers: {
      "X-Auth-Token": token,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Verification failed" }));
    throw new Error(err.detail || "Verification failed");
  }

  return res.json();
}

export async function verifyDocument(recordId: string, role: string = "REGISTRAR"): Promise<ExtractionResult> {
  const token = role === "OPERATOR" ? "operator-token-sih2026" : "registrar-token-sih2026";
  const res = await fetch(`${BASE_URL}/records/${recordId}/verify`, {
    method: "POST",
    headers: {
      "X-Auth-Token": token,
    },
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

export async function getRecords(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/records`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch records" }));
    throw new Error(err.detail || "Failed to fetch records");
  }

  return res.json();
}
