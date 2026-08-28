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

    def extract(self, ocr_result: OCRResult) -> ExtractionResult:
        """
        Parses OCRResult and returns extracted fields with provenance tracking.
        """
        extracted_fields: List[ExtractedField] = []
        
        # We will attempt to extract each field
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
        
        elements = ocr_result.elements
        
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
                val = match.group(1).strip()
                # Remove trailing punctuations if regex caught any
                val = re.sub(r"^[:\-\s]+|[:\-\s]+$", "", val)
                if val:
                    # Ignore values that are actually label names (false positives)
                    if val.lower() in {"name", "number", "no", "area", "village", "tehsil", "district", "rict", "value", "uni", "total"}:
                        continue
                    return ExtractedField(
                        name=name,
                        value=val,
                        status="SUCCESS",
                        source_elements=[element],
                        explanation=f"Extracted directly from line: '{element.text}' via regex."
                    )
                    
        # Step 2: Check for keyword presence and use spatial layout heuristics
        for idx, element in enumerate(elements):
            text_lower = element.text.lower()
            # If we find a keyword in this text element
            if any(re.search(rf"\b{kw}\b", text_lower) for kw in keywords):
                # Check if there is a next element in reading order that is physically close
                # or if the keyword block has some text we can clean up
                
                # Check the immediate next element (simple reading order heuristic)
                if idx + 1 < len(elements):
                    next_el = elements[idx + 1]
                    # Ensure next element doesn't contain other keywords
                    if not any(re.search(rf"\b{kw}\b", next_el.text.lower()) for kw in keywords):
                        # Clean up value candidate (avoid labels)
                        candidate_value = next_el.text.strip()
                        # Verify candidate looks like a value, not a different label
                        if candidate_value and len(candidate_value) < 100 and ":" not in candidate_value:
                            # Verify if it makes sense spatially (either horizontally aligned or below)
                            if self._is_spatially_aligned(element.bbox, next_el.bbox):
                                if candidate_value.lower() not in {"name", "number", "no", "area", "village", "tehsil", "district", "value", "uni", "total"}:
                                    return ExtractedField(
                                        name=name,
                                        value=candidate_value,
                                        status="SUCCESS",
                                        source_elements=[element, next_el],
                                        explanation=f"Extracted spatial neighbor: '{candidate_value}' aligned with keyword '{element.text}'."
                                    )
                                
                # Check for horizontal neighbor to the right (strict geometry)
                right_neighbor = self._find_right_neighbor(element, elements)
                if right_neighbor:
                    candidate_value = right_neighbor.text.strip()
                    if candidate_value and ":" not in candidate_value:
                        if candidate_value.lower() not in {"name", "number", "no", "area", "village", "tehsil", "district", "value", "uni", "total"}:
                            return ExtractedField(
                                name=name,
                                value=candidate_value,
                                status="SUCCESS",
                                source_elements=[element, right_neighbor],
                                explanation=f"Extracted geometric neighbor to the right: '{candidate_value}'."
                            )
                        
        # If we found keywords but couldn't find a clean value
        for element in elements:
            if any(re.search(rf"\b{kw}\b", element.text.lower()) for kw in keywords):
                return ExtractedField(
                    name=name,
                    value=None,
                    status="UNCERTAIN",
                    source_elements=[element],
                    explanation=f"Keyword '{element.text}' found, but no matching value could be extracted."
                )

        # Field not found at all
        return ExtractedField(
            name=name,
            value=None,
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
