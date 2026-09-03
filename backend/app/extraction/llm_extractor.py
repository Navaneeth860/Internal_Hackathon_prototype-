import re
import os
import json
import logging
import ollama
from typing import List, Dict, Any, Optional
from backend.app.ocr.ocr_models import OCRResult, OCRElement
from backend.app.extraction.schemas import ExtractedField, ExtractionResult
from backend.app.extraction.deed_schemas import DOCUMENT_TYPE_SCHEMAS

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    Helper to normalize text for alignment matches.
    """
    # Keep Unicode letters so Kannada values can be aligned to OCR evidence.
    return re.sub(r"[^\w]", "", text.casefold(), flags=re.UNICODE)

class LLMExtractor:
    """
    LLMExtractor communicates with local Ollama service to perform
    contextual/semantic extraction based on extensible deed schemas.
    """
    
    def __init__(self):
        self.model_name = os.environ.get("OLLAMA_MODEL", "llama3")

    def extract(self, ocr_result: OCRResult, document_subtype: str) -> Optional[ExtractionResult]:
        """
        Extracts structured fields using local LLM based on the document subtype.
        If Ollama is offline or parsing fails, returns None (triggering keyword fallback).
        """
        if document_subtype not in DOCUMENT_TYPE_SCHEMAS:
            logger.info(f"Subtype '{document_subtype}' has no extensible schema. Skipping LLM extraction.")
            return None
            
        schema = DOCUMENT_TYPE_SCHEMAS[document_subtype]
        ocr_text = " ".join(el.text for el in ocr_result.elements)
        
        # Build prompt listing the target fields and their description specification
        schema_instructions = []
        for spec in schema:
            schema_instructions.append(
                f"- Name: '{spec['name']}'\n"
                f"  Description: {spec['description']}\n"
                f"  Example: {spec['example']}"
            )
            
        fields_bullet_list = "\n".join(schema_instructions)
        
        prompt = (
            "You are an expert legal document processing system specializing in Indian land records and deed documents.\n"
            "Analyze the following document text and extract the fields listed below.\n\n"
            "STRICT RULES — follow every rule exactly:\n"
            "1. Return ONLY a valid JSON object. No preamble, no explanation, no markdown fences.\n"
            "2. FULL NAMES ONLY: For any name field (seller, buyer, parties, owner), always extract the COMPLETE full name as written in the document. "
            "Never return only a surname. E.g. if the document says 'Ramesh Kumar', return 'Ramesh Kumar', not 'Kumar'.\n"
            "3. DATES: Normalize all dates to DD-MM-YYYY format. "
            "Handle all formats: '15-06-2025', '15/06/2025', '15th June 2025', '15 June 2025', 'June 15, 2025'. "
            "Example: '15th July 2026' → '15-07-2026'.\n"
            "4. SEMANTIC ROLES: Identify roles from legal prose. "
            "'hereinafter referred to as the Vendor/Seller' = seller_name. "
            "'hereinafter referred to as the Purchaser/Buyer' = buyer_name. "
            "'sale consideration of Rs. X' = sale_consideration.\n"
            "5. If a field is genuinely absent from the text, set its value to null.\n"
            "6. If a field is ambiguous or unclear, set its value to 'UNCERTAIN'.\n"
            "7. Do NOT invent or hallucinate values not present in the text.\n\n"
            "8. The document may contain Kannada, English names, and numerals. Preserve "
            "the original Unicode spelling of values; do not transliterate it.\n\n"
            "Target Fields Schema:\n"
            f"{fields_bullet_list}\n\n"
            f"Document Text:\n{ocr_text[:4000]}\n\n"
            "JSON Response:"
        )
        
        try:
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            client = ollama.Client(host=host)
            
            # Verify server connectivity
            try:
                client.list()
            except Exception as conn_err:
                logger.warning(f"Could not connect to Ollama server at {host}: {conn_err}")
                return None
                
            response = client.generate(model=self.model_name, prompt=prompt)
            raw_response = response.get("response", "").strip()
            logger.info("Received LLM raw response for extraction.")
            
            parsed_json = self._parse_json(raw_response)
            if not parsed_json:
                logger.warning("Failed to parse JSON from LLM response.")
                return None
                
            extracted_fields: List[ExtractedField] = []
            
            for spec in schema:
                name = spec["name"]
                val = parsed_json.get(name)
                
                # Post-process the raw value before storing
                if isinstance(val, str):
                    val = self._normalize_value(name, val.strip())
                
                # Determine status and value details
                status = "SUCCESS"
                if val is None:
                    status = "NOT_PRESENT"
                elif val == "UNCERTAIN":
                    status = "UNCERTAIN"
                    val = None
                    
                # Map extracted value back to OCR evidence coordinates
                source_elements = []
                explanation = f"Extracted semantically via LLM based on schema description: '{spec['description']}'."
                
                if val:
                    source_elements = self._align_evidence(val, ocr_result.elements)
                    if source_elements:
                        explanation += f" Linked to OCR element evidence: '{source_elements[0].text}'."
                    else:
                        explanation += " Extracted from document semantic context (no direct OCR bounding box mapped)."
                        
                field = ExtractedField(
                    name=name,
                    value=val,
                    original_value=val,
                    status=status,
                    source_elements=source_elements,
                    explanation=explanation
                )
                extracted_fields.append(field)
                
            return ExtractionResult(
                fields=extracted_fields,
                document_subtype=document_subtype,
                extraction_method="llm"
            )
        except Exception as e:
            logger.warning(f"Ollama extraction failed (Ollama server might be offline): {e}")
            return None

    def _normalize_value(self, field_name: str, val: str) -> Optional[str]:
        """
        Post-processes a raw LLM string value:
        - Collapses extra whitespace in name fields
        - Normalizes dates to DD-MM-YYYY (handles ordinal suffixes and word months)
        """
        if not val or not val.strip():
            return None

        val = " ".join(val.split())  # collapse multiple spaces

        if "date" in field_name:
            # Month name → number mapping
            month_map = {
                "january": "01", "february": "02", "march": "03", "april": "04",
                "may": "05", "june": "06", "july": "07", "august": "08",
                "september": "09", "october": "10", "november": "11", "december": "12",
                "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                "jun": "06", "jul": "07", "aug": "08",
                "sep": "09", "oct": "10", "nov": "11", "dec": "12"
            }
            # Handle "15th July 2026", "15 July 2026", "July 15, 2026" etc.
            word_date = re.match(
                r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", val
            )
            if word_date:
                day, mon_str, year = word_date.groups()
                mon = month_map.get(mon_str.lower())
                if mon:
                    return f"{int(day):02d}-{mon}-{year}"
            # Handle "July 15, 2026" or "July 15 2026"
            word_date2 = re.match(
                r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", val
            )
            if word_date2:
                mon_str, day, year = word_date2.groups()
                mon = month_map.get(mon_str.lower())
                if mon:
                    return f"{int(day):02d}-{mon}-{year}"
            # Standardise slash → dash  e.g. 15/06/2025
            val = re.sub(r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\1-\2-\3", val)

        return val

    def _parse_json(self, raw_str: str) -> Optional[Dict[str, Any]]:

        """
        Robust JSON extractor that finds JSON blocks inside arbitrary markdown or preamble strings.
        """
        # Find first '{' and last '}'
        start = raw_str.find("{")
        end = raw_str.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return None
            
        json_str = raw_str[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try basic escapes cleanup if decoding fails
            try:
                # Remove common invalid escapes/fences
                cleaned = re.sub(r'\\([^"/\\bfnrtu])', r'\1', json_str)
                return json.loads(cleaned)
            except Exception:
                return None

    def _align_evidence(self, value: str, elements: List[OCRElement]) -> List[OCRElement]:
        """
        Lightweight text alignment matching to locate bounding boxes.
        """
        matched = []
        norm_val = normalize_text(value)
        if not norm_val:
            return matched
            
        # 1. Look for exact or subset matches
        for el in elements:
            norm_el = normalize_text(el.text)
            if norm_val in norm_el or norm_el in norm_val:
                matched.append(el)
                
        # 2. Look for word overlap matches if subset failed
        if not matched:
            val_words = set(norm_val.split())
            if len(val_words) > 1:
                for el in elements:
                    el_words = set(normalize_text(el.text).split())
                    # If at least 2 words overlap
                    if len(val_words.intersection(el_words)) >= 2:
                        matched.append(el)
                        
        return matched
