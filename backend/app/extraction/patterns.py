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
    rf"\b(?:{'|'.join(AREA_KEYWORDS)})\b[:\-]?\s*([0-9\.\-\s]+(?:\w+|Hec|Acres|Hectares|Bigha)?)", 
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
