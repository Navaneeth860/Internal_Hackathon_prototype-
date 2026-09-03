import re
import os
import logging
from typing import Optional
from backend.app.ocr.ocr_models import OCRResult

logger = logging.getLogger(__name__)

# Heuristic keyword match lists
SALE_DEED_KEYWORDS = [
    r"\bdeed of sale\b",
    r"\bsale deed\b",
    r"\bconveyance deed\b",
    r"\bvendor\b",
    r"\bpurchaser\b",
    r"\bsale consideration\b",
    r"\bagreed to sell\b",
    r"\bagreed to purchase\b",
    r"\bconvey\b",
    r"\btransfer\b",
    r"\babsolute sale\b"
]

PARTITION_DEED_KEYWORDS = [
    r"\bdeed of partition\b",
    r"\bpartition deed\b",
    r"\bpartition\b",
    r"\bco-owners\b",
    r"\bjointly held\b",
    r"\brespective share\b",
    r"\bdivide\b",
    r"\bpartitioned\b",
    r"\ballotted share\b"
]

# Karnataka sale-deed headings and terms. A document must contain more than a
# heading alone before it is classified as a Kannada Sale Deed.
KANNADA_SALE_DEED_KEYWORDS = [
    "ಮಾರಾಟ ಪತ್ರ", "ಮಾರಾಟದ ಪತ್ರ", "ಕ್ರಯಪತ್ರ", "ಕ್ರಯ ಪತ್ರ",
    "ಮಾರಾಟ ದಸ್ತಾವೇಜು", "ಮಾರಾಟದ ದಸ್ತಾವೇಜು", "ಕ್ರಯದ ದಸ್ತಾವೇಜು",
]
KANNADA_SALE_CONTEXT = [
    "ಮಾರಾಟ", "ಕ್ರಯ", "ಮಾರಾಟದ ಮೊತ್ತ", "ಮಾರಾಟದ ಪರಿಗಣನೆ", "ಖಾತೆ",
    "ಸರ್ವೇ", "ಹಿಸ್ಸಾ", "ಖರೀದಿದಾರ", "ಮಾರಾಟಗಾರ", "ನೋಂದಣಿ",
]

class DocumentClassifier:
    """
    DocumentClassifier uses a two-level classification strategy:
    Level 1: Deterministic heuristic based on keyword occurrence counts.
    Level 2: Local LLM fallback (via Ollama) when heuristics are inconclusive.
    """
    
    def __init__(self):
        self.model_name = os.environ.get("OLLAMA_MODEL", "llama3")

    def classify(self, ocr_result: OCRResult) -> str:
        """
        Classifies a document based on its OCR text.
        Returns "Sale Deed", "Partition Deed", or "Unknown".
        """
        ocr_text = " ".join(el.text for el in ocr_result.elements)
        text_lower = ocr_text.lower()
        
        # Level 1: Deterministic heuristic checks
        sale_hits = sum(1 for kw in SALE_DEED_KEYWORDS if re.search(kw, text_lower))
        partition_hits = sum(1 for kw in PARTITION_DEED_KEYWORDS if re.search(kw, text_lower))
        kannada_heading_hits = sum(1 for kw in KANNADA_SALE_DEED_KEYWORDS if kw in ocr_text)
        kannada_context_hits = sum(1 for kw in KANNADA_SALE_CONTEXT if kw in ocr_text)
        
        logger.info(
            "Classifier heuristics: Sale=%s, Partition=%s, Kannada heading=%s, Kannada context=%s",
            sale_hits, partition_hits, kannada_heading_hits, kannada_context_hits,
        )
        
        # If we have strong signal (at least 2 distinct keywords), use heuristic directly
        if kannada_heading_hits >= 1 and kannada_context_hits >= 2:
            logger.info("Classified as Kannada Sale Deed via Level 1 heuristics.")
            return "Kannada Sale Deed"
        if sale_hits >= 2 and sale_hits > partition_hits:
            logger.info("Classified as Sale Deed via Level 1 heuristics.")
            return "Sale Deed"
        elif partition_hits >= 2 and partition_hits > sale_hits:
            logger.info("Classified as Partition Deed via Level 1 heuristics.")
            return "Partition Deed"
            
        # Level 2: Local LLM fallback
        logger.info("Heuristics inconclusive. Falling back to Level 2 LLM classification...")
        try:
            import ollama as _ollama
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            client = _ollama.Client(host=host)
            
            # Verify connectivity before calling generate
            try:
                client.list()
            except Exception as conn_err:
                logger.warning(f"Could not connect to Ollama at {host} for classification: {conn_err}")
                return "Unknown"
                
            prompt = (
                "You are an expert legal assistant. Classify the following land record document text into exactly one of these types:\n"
                "- Sale Deed\n"
                "- Kannada Sale Deed\n"
                "- Partition Deed\n"
                "- Unknown\n\n"
                "Respond with ONLY the classification name, nothing else. No preamble, no explanation, no markdown formatting.\n\n"
                f"Document Text:\n{ocr_text[:3000]}"  # limit length to avoid overwhelming prompt context
            )
            
            response = client.generate(model=self.model_name, prompt=prompt)
            response_text = response.get("response", "").strip()
            logger.info(f"LLM Classifier Response: '{response_text}'")
            
            if "kannada sale deed" in response_text.lower():
                return "Kannada Sale Deed"
            if "sale deed" in response_text.lower():
                return "Sale Deed"
            elif "partition deed" in response_text.lower():
                return "Partition Deed"
            else:
                return "Unknown"
        except Exception as e:
            logger.warning(f"Ollama classification failed (Ollama server might be offline): {e}")
            return "Unknown"
