export interface OCRElement {
  text: string;
  confidence: number;
  bbox: [number, number][];
  normalized_bbox?: [number, number][];
}

export interface ExtractedField {
  name: string;
  value: string | null;
  original_value: string | null;
  corrected_value: string | null;
  status: string; // "SUCCESS", "MISSING", "UNCERTAIN", "NOT_PRESENT"
  verification_status: string; // "UNVERIFIED", "VERIFIED", "CORRECTED"
  verified_at: string | null;
  confidence: number;
  source_elements: OCRElement[];
  validation_warnings: string[];
  explanation: string | null;
}

export interface ExtractionResult {
  fields: ExtractedField[];
  document_type: string;
  document_subtype?: string;
  extraction_method?: string;
  image_url: string | null;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
}

