import re
import logging
from typing import List, Optional, Tuple
from backend.app.ocr.ocr_models import OCRResult, OCRElement
from backend.app.extraction.schemas import ExtractedField, ExtractionResult
from backend.app.extraction import patterns

logger = logging.getLogger(__name__)

class FieldExtractor:
    """
    FieldExtractor performs rule-based and spatial extraction of key fields
    from OCRResult text and bounding boxes.
    """
    
    def __init__(self):
        pass

    def _clean_extracted_value(self, name: str, val: str) -> Optional[str]:
        """
        Cleans and filters extracted values to prevent raw prose/garbage leaks.
        Returns None if the value fails name, numeric, or prose checks.
        """
        cleaned = val.strip()
        if not cleaned:
            return None
            
        # 1. Length guard
        if len(cleaned) > 80:
            return None
            
        # 2. Key-value name checks (e.g. names should look like names, not prose clauses)
        if name in ["owner_name", "seller_name", "buyer_name", "parties"]:
            lower_val = cleaned.lower()
            
            # If it starts with common prepositions or conjunctions
            prepositions = {"of", "to", "and", "the", "for", "by", "with", "in", "on", "at", "between", "under"}
            first_word = lower_val.split()[0] if lower_val.split() else ""
            if first_word in prepositions:
                return None
                
            invalid_sub_words = {
                "agricultural", "land", "situated", "described", "property", "possessor",
                "herein", "hereinafter", "referred", "called", "vendor", "purchaser",
                "buyer", "seller", "sole", "absolute", "owner", "possession", "below",
                "east", "west", "north", "south", "boundary", "boundaries", "having",
                "measuring", "agreement", "witnesseth", "first part", "second part",
                "resident", "residing", "daughter", "son", "wife"
            }
            
            # Check for intersections with invalid sentence/clause keywords
            words = set(re.findall(r"\b\w+\b", lower_val))
            if words.intersection(invalid_sub_words):
                return None
                
        # 3. Numeric checks (e.g. survey_number should contain digits)
        if name in ["survey_number", "khasra_number", "khata_number", "party_count"]:
            if not any(char.isdigit() for char in cleaned):
                return None
                
        return cleaned

    def extract(self, ocr_result: OCRResult, subtype: Optional[str] = None) -> ExtractionResult:
        """
        Parses OCRResult and returns extracted fields with provenance tracking.
        Adapts dynamically based on the document subtype.
        """
        extracted_fields: List[ExtractedField] = []
        elements = ocr_result.elements
        
        # Determine target fields based on document subtype
        if subtype == "Sale Deed":
            fields_to_extract = [
                ("document_date", re.compile(r"(\b\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b)", re.I), ["date", "executed"]),
                ("seller_name", re.compile(r"between\s+([A-Z][a-zA-Z\s]+?)(?:,|\s+resident|\s+hereinafter)", re.I), ["seller", "vendor"]),
                ("buyer_name", re.compile(r"and\s+([A-Z][a-zA-Z\s]+?)(?:,|\s+resident|\s+hereinafter)", re.I), ["buyer", "purchaser"]),
                ("sale_consideration", re.compile(r"(?:consideration|rs\.?|rupees|price)\s*(?:of\s*)?([0-9,]+(?:\.\d+)?)\b", re.I), ["consideration", "price", "amount"]),
                ("survey_number", patterns.SURVEY_PATTERN, patterns.SURVEY_KEYWORDS),
                ("area", patterns.AREA_PATTERN, patterns.AREA_KEYWORDS),
                ("property_location", re.compile(r"(?:location|situated\s+at)\s*[:\-]?\s*([A-Za-z0-9\s,]+)", re.I), ["location", "situated"]),
                ("village", patterns.VILLAGE_PATTERN, patterns.VILLAGE_KEYWORDS),
                ("district", patterns.DISTRICT_PATTERN, patterns.DISTRICT_KEYWORDS),
                ("registration_details", re.compile(r"\b(?:reg|registration|doc)\s*(?:no\.?|number)?\s*([A-Za-z0-9\-]+)\b", re.I), ["registration", "reg"]),
                ("seller_address", re.compile(r"(?:seller|vendor)\s+(?:address|resident\s+of)\s*[:\-]?\s*([A-Za-z0-9\s,]+)", re.I), ["seller address", "vendor address"]),
                ("buyer_address", re.compile(r"(?:buyer|purchaser)\s+(?:address|resident\s+of)\s*[:\-]?\s*([A-Za-z0-9\s,]+)", re.I), ["buyer address", "purchaser address"])
            ]
        elif subtype == "Partition Deed":
            fields_to_extract = [
                ("document_date", re.compile(r"\b\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4}\b", re.I), ["date", "executed"]),
                ("parties", re.compile(r"(?:among|between)\s+([A-Za-z\s,]+?)(?:\s+who|\s+are|\.|\n)", re.I), ["parties", "co-owners"]),
                ("party_count", re.compile(r"(?:party\s+count|co-owners\s+count|parties\s+count)\s*[:\-]?\s*([0-9]+)\b", re.I), ["party count", "co-owners count"]),
                ("survey_number", patterns.SURVEY_PATTERN, patterns.SURVEY_KEYWORDS),
                ("total_area", patterns.AREA_PATTERN, patterns.AREA_KEYWORDS),
                ("share_allocation", re.compile(r"(?:share|allocation)\s*[:\-]?\s*([A-Za-z0-9\s,\.]+)", re.I), ["share", "allocation"]),
                ("village", patterns.VILLAGE_PATTERN, patterns.VILLAGE_KEYWORDS),
                ("district", patterns.DISTRICT_PATTERN, patterns.DISTRICT_KEYWORDS),
                ("property_description", re.compile(r"(?:description|details)\s*[:\-]?\s*([A-Za-z0-9\s,]+)", re.I), ["description", "boundaries"]),
                ("registration_details", re.compile(r"\b(?:reg|registration|doc)\s*(?:no\.?|number)?\s*([A-Za-z0-9\-]+)\b", re.I), ["registration", "reg"])
            ]
        else:
            fields_to_extract = [
                ("owner_name", patterns.OWNER_PATTERN, patterns.OWNER_KEYWORDS),
                ("survey_number", patterns.SURVEY_PATTERN, patterns.SURVEY_KEYWORDS),
                ("khasra_number", patterns.KHASRA_PATTERN, patterns.KHASRA_KEYWORDS),
                ("khata_number", patterns.KHATA_PATTERN, patterns.KHATA_KEYWORDS),
                ("area", patterns.AREA_PATTERN, patterns.AREA_KEYWORDS),
                ("village", patterns.VILLAGE_PATTERN, patterns.VILLAGE_KEYWORDS),
                ("tehsil", patterns.TEHSIL_PATTERN, patterns.TEHSIL_KEYWORDS),
                ("district", patterns.DISTRICT_PATTERN, patterns.DISTRICT_KEYWORDS),
            ]
        
        for name, pattern, keywords in fields_to_extract:
            field = self._extract_field(name, pattern, keywords, elements)
            extracted_fields.append(field)
            
        return ExtractionResult(fields=extracted_fields)

    def _extract_field(
        self, 
        name: str, 
        pattern: re.Pattern, 
        keywords: List[str], 
        elements: List[OCRElement]
    ) -> ExtractedField:
        """
        Extracts a single field by checking:
        1. Single-line pattern match (e.g. "Survey No: 124/3")
        2. Multi-line pattern match or spatial check (value is to the right or below keyword)
        """
        # Step 1: Check single-line matches
        for element in elements:
            match = pattern.search(element.text)
            if match:
                # Use group(1) if pattern has capture groups, else full match
                val = (match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)).strip()
                val = re.sub(r"^[:\-\s]+|[:\-\s]+$", "", val)
                cleaned_val = self._clean_extracted_value(name, val)
                if cleaned_val:
                    if cleaned_val.lower() in {"name", "number", "no", "area", "village", "tehsil", "district", "value", "uni", "total"}:
                        continue
                    return ExtractedField(
                        name=name,
                        value=cleaned_val,
                        original_value=cleaned_val,
                        status="SUCCESS",
                        source_elements=[element],
                        explanation=f"Extracted directly from line: '{element.text}' via regex."
                    )
                    
        # Step 2: Check for keyword presence and use spatial layout heuristics
        for idx, element in enumerate(elements):
            text_lower = element.text.lower()
            if any(re.search(rf"\b{kw}\b", text_lower) for kw in keywords):
                # Check the immediate next element (simple reading order heuristic)
                if idx + 1 < len(elements):
                    next_el = elements[idx + 1]
                    if not any(re.search(rf"\b{kw}\b", next_el.text.lower()) for kw in keywords):
                        candidate_value = next_el.text.strip()
                        cleaned_cand = self._clean_extracted_value(name, candidate_value)
                        if cleaned_cand and len(cleaned_cand) < 100 and ":" not in cleaned_cand:
                            if self._is_spatially_aligned(element.bbox, next_el.bbox):
                                if cleaned_cand.lower() not in {"name", "number", "no", "area", "village", "tehsil", "district", "value", "uni", "total"}:
                                    return ExtractedField(
                                        name=name,
                                        value=cleaned_cand,
                                        original_value=cleaned_cand,
                                        status="SUCCESS",
                                        source_elements=[element, next_el],
                                        explanation=f"Extracted spatial neighbor: '{cleaned_cand}' aligned with keyword '{element.text}'."
                                    )
                                
                # Check for horizontal neighbor to the right (strict geometry)
                right_neighbor = self._find_right_neighbor(element, elements)
                if right_neighbor:
                    candidate_value = right_neighbor.text.strip()
                    cleaned_right = self._clean_extracted_value(name, candidate_value)
                    if cleaned_right and ":" not in cleaned_right:
                        if cleaned_right.lower() not in {"name", "number", "no", "area", "village", "tehsil", "district", "value", "uni", "total"}:
                            return ExtractedField(
                                name=name,
                                value=cleaned_right,
                                original_value=cleaned_right,
                                status="SUCCESS",
                                source_elements=[element, right_neighbor],
                                explanation=f"Extracted geometric neighbor to the right: '{cleaned_right}'."
                            )
                        
        # If we found keywords but couldn't extract/validate a clean value
        for element in elements:
            if any(re.search(rf"\b{kw}\b", element.text.lower()) for kw in keywords):
                return ExtractedField(
                    name=name,
                    value=None,
                    original_value=None,
                    status="UNCERTAIN",
                    source_elements=[element],
                    explanation=f"Keyword '{element.text}' found, but no matching value could be extracted."
                )

        # Field not found at all
        return ExtractedField(
            name=name,
            value=None,
            original_value=None,
            status="NOT_PRESENT",
            source_elements=[],
            explanation="Field not present in the document."
        )

    def _is_spatially_aligned(self, bbox_label: List[Tuple[float, float]], bbox_value: List[Tuple[float, float]]) -> bool:
        """
        Checks if two bounding boxes are aligned horizontally or vertically.
        Bbox points: [top-left, top-right, bottom-right, bottom-left]
        """
        # Get bounds
        ly_min = min(pt[1] for pt in bbox_label)
        ly_max = max(pt[1] for pt in bbox_label)
        vy_min = min(pt[1] for pt in bbox_value)
        vy_max = max(pt[1] for pt in bbox_value)
        
        # Check vertical overlap (horizontal alignment)
        overlap = min(ly_max, vy_max) - max(ly_min, vy_min)
        label_height = ly_max - ly_min
        value_height = vy_max - vy_min
        min_height = min(label_height, value_height)
        
        if min_height > 0 and (overlap / min_height) > 0.4:
            # Check horizontal distance is reasonable
            lx_max = max(pt[0] for pt in bbox_label)
            vx_min = min(pt[0] for pt in bbox_value)
            dist = vx_min - lx_max
            if 0 <= dist <= 300:  # Allow up to 300 pixels separation
                return True
                
        # Check vertical alignment (value is directly below label)
        lx_min = min(pt[0] for pt in bbox_label)
        lx_max = max(pt[0] for pt in bbox_label)
        vx_min = min(pt[0] for pt in bbox_value)
        vx_max = max(pt[0] for pt in bbox_value)
        
        horiz_overlap = min(lx_max, vx_max) - max(lx_min, vx_min)
        label_width = lx_max - lx_min
        if label_width > 0 and (horiz_overlap / label_width) > 0.4:
            # Check vertical distance
            ly_max = max(pt[1] for pt in bbox_label)
            vy_min = min(pt[1] for pt in bbox_value)
            v_dist = vy_min - ly_max
            if 0 <= v_dist <= 100:  # Allow up to 100 pixels below
                return True
                
        return False

    def _find_right_neighbor(self, target: OCRElement, elements: List[OCRElement]) -> Optional[OCRElement]:
        """
        Finds the closest OCR element situated immediately to the right of the target.
        """
        t_lx_max = max(pt[0] for pt in target.bbox)
        t_ly_min = min(pt[1] for pt in target.bbox)
        t_ly_max = max(pt[1] for pt in target.bbox)
        t_height = t_ly_max - t_ly_min
        
        best_candidate = None
        min_dist = float("inf")
        
        for el in elements:
            if el == target:
                continue
                
            el_vx_min = min(pt[0] for pt in el.bbox)
            # Must be to the right
            if el_vx_min < t_lx_max:
                continue
                
            el_vy_min = min(pt[1] for pt in el.bbox)
            el_vy_max = max(pt[1] for pt in el.bbox)
            
            # Must overlap vertically
            overlap = min(t_ly_max, el_vy_max) - max(t_ly_min, el_vy_min)
            el_height = el_vy_max - el_vy_min
            min_h = min(t_height, el_height)
            
            if min_h > 0 and (overlap / min_h) > 0.5:
                dist = el_vx_min - t_lx_max
                if dist < min_dist and dist < 400:
                    min_dist = dist
                    best_candidate = el
                    
        return best_candidate
