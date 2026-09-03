import re

# Keywords and Regex patterns for matching land record fields
# Wrap keyword unions in \b to prevent prefix matching issues

# Owner Name
OWNER_KEYWORDS = [
    r"owner\s*name", r"name\s*of\s*owner", r"land\s*owner", r"patta\s*dar", 
    r"khatedar", r"possessor", r"owner"
]
OWNER_PATTERN = re.compile(
    rf"\b(?:{'|'.join(OWNER_KEYWORDS)})\b[:\-]?\s*([A-Za-z\s\.\(\)\'\-]+)", 
    re.IGNORECASE
)

# Survey Number
SURVEY_KEYWORDS = [r"survey\s*number", r"survey\s*no", r"survey"]
SURVEY_PATTERN = re.compile(
    rf"\b(?:{'|'.join(SURVEY_KEYWORDS)})\b[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Khasra Number
KHASRA_KEYWORDS = [r"khasra\s*number", r"khasra\s*no", r"khasra"]
KHASRA_PATTERN = re.compile(
    rf"\b(?:{'|'.join(KHASRA_KEYWORDS)})\b[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Khata Number
KHATA_KEYWORDS = [r"khata\s*number", r"khata\s*no", r"khata\s*uni", r"khata"]
KHATA_PATTERN = re.compile(
    rf"\b(?:{'|'.join(KHATA_KEYWORDS)})\b[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Area
AREA_KEYWORDS = [r"total\s*area", r"land\s*area", r"area"]
AREA_PATTERN = re.compile(
    rf"\b(?:{'|'.join(AREA_KEYWORDS)})\b.*?\b(\d+(?:\.\d+)?\s*(?:acres?|hectares?|hec\b|ha\b|sq\s*ft|sqm|sq\s*yards?|bighas?|sq\.\s*ft\b)?)", 
    re.IGNORECASE
)

# Village
VILLAGE_KEYWORDS = [r"village\s*name", r"village", r"mauza"]
VILLAGE_PATTERN = re.compile(
    rf"\b(?:{'|'.join(VILLAGE_KEYWORDS)})\b[:\-]?\s*([A-Za-z0-9\s]+)", 
    re.IGNORECASE
)

# Tehsil
TEHSIL_KEYWORDS = [r"tehsil", r"taluk", r"sub\-division", r"taluka"]
TEHSIL_PATTERN = re.compile(
    rf"\b(?:{'|'.join(TEHSIL_KEYWORDS)})\b[:\-]?\s*([A-Za-z\s]+)", 
    re.IGNORECASE
)

# District
DISTRICT_KEYWORDS = [r"district", r"zila", r"dist"]
DISTRICT_PATTERN = re.compile(
    rf"\b(?:{'|'.join(DISTRICT_KEYWORDS)})\b[:\-]?\s*([A-Za-z\s]+)", 
    re.IGNORECASE
)


def label_value_pattern(*labels: str) -> re.Pattern:
    """Build a Unicode-safe label/value pattern for Kannada/English OCR lines."""
    escaped = "|".join(re.escape(label) for label in labels)
    return re.compile(rf"(?:{escaped})\s*[:\-]?\s*(.+)$", re.IGNORECASE)


KANNADA_SALE_DEED_FIELD_SPECS = [
    ("document_date", re.compile(r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"), ["ದಿನಾಂಕ", "date", "executed"]),
    ("seller_name", label_value_pattern("ಮಾರಾಟಗಾರ", "ಮಾರಾಟದಾರ", "seller", "vendor"), ["ಮಾರಾಟಗಾರ", "seller", "vendor"]),
    ("seller_address", label_value_pattern("ಮಾರಾಟಗಾರರ ವಿಳಾಸ", "seller address", "vendor address"), ["ಮಾರಾಟಗಾರರ ವಿಳಾಸ", "seller address"]),
    ("buyer_name", label_value_pattern("ಖರೀದಿದಾರ", "ಖರೀದಿದಾರೆ", "buyer", "purchaser"), ["ಖರೀದಿದಾರ", "buyer", "purchaser"]),
    ("buyer_address", label_value_pattern("ಖರೀದಿದಾರರ ವಿಳಾಸ", "buyer address", "purchaser address"), ["ಖರೀದಿದಾರರ ವಿಳಾಸ", "buyer address"]),
    ("khata_number", label_value_pattern("ಖಾತೆ ಸಂಖ್ಯೆ", "khata number", "khata"), ["ಖಾತೆ", "khata"]),
    ("survey_number", label_value_pattern("ಸರ್ವೇ ಸಂಖ್ಯೆ", "survey number", "survey no"), ["ಸರ್ವೇ", "survey"]),
    ("area", label_value_pattern("ವಿಸ್ತೀರ್ಣ", "ಕ್ಷೇತ್ರಫಲ", "area", "extent"), ["ವಿಸ್ತೀರ್ಣ", "ಕ್ಷೇತ್ರಫಲ", "area", "extent"]),
    ("road", label_value_pattern("ರಸ್ತೆ", "road", "street"), ["ರಸ್ತೆ", "road", "street"]),
    ("village", label_value_pattern("ಗ್ರಾಮ", "village"), ["ಗ್ರಾಮ", "village"]),
    ("taluk", label_value_pattern("ತಾಲ್ಲೂಕು", "ತಾಲೂಕು", "taluk", "taluka"), ["ತಾಲ್ಲೂಕು", "ತಾಲೂಕು", "taluk"]),
    ("district", label_value_pattern("ಜಿಲ್ಲೆ", "district"), ["ಜಿಲ್ಲೆ", "district"]),
    ("city", label_value_pattern("ನಗರ", "city"), ["ನಗರ", "city"]),
    ("state", label_value_pattern("ರಾಜ್ಯ", "state"), ["ರಾಜ್ಯ", "state"]),
]

