import re

# Keywords and Regex patterns for matching land record fields

# Owner Name
OWNER_KEYWORDS = [
    r"owner\s*name", r"name\s*of\s*owner", r"land\s*owner", r"patta\s*dar", 
    r"khatedar", r"possessor", r"owner"
]
OWNER_PATTERN = re.compile(
    rf"(?:{'|'.join(OWNER_KEYWORDS)})[:\-]?\s*([A-Za-z\s\.\(\)\'\-]+)", 
    re.IGNORECASE
)

# Survey Number
SURVEY_KEYWORDS = [r"survey\s*number", r"survey\s*no", r"survey"]
# Matches patterns like 124/3, 124-A, 87, 45/2B
SURVEY_PATTERN = re.compile(
    rf"(?:{'|'.join(SURVEY_KEYWORDS)})[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Khasra Number
KHASRA_KEYWORDS = [r"khasra\s*number", r"khasra\s*no", r"khasra"]
KHASRA_PATTERN = re.compile(
    rf"(?:{'|'.join(KHASRA_KEYWORDS)})[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Khata Number
KHATA_KEYWORDS = [r"khata\s*number", r"khata\s*no", r"khata\s*uni", r"khata"]
KHATA_PATTERN = re.compile(
    rf"(?:{'|'.join(KHATA_KEYWORDS)})[:\-]?\s*([0-9]+[A-Za-z0-9\/\-\s]*)", 
    re.IGNORECASE
)

# Area
AREA_KEYWORDS = [r"total\s*area", r"land\s*area", r"area"]
# Matches values like 2.45 acres, 1.25 hectares, 0.45 Hec., 3-12-0 bighas
AREA_PATTERN = re.compile(
    rf"(?:{'|'.join(AREA_KEYWORDS)})[:\-]?\s*([0-9\.\-\s]+(?:\w+|Hec|Acres|Hectares|Bigha)?)", 
    re.IGNORECASE
)

# Village
VILLAGE_KEYWORDS = [r"village\s*name", r"village", r"mauza"]
VILLAGE_PATTERN = re.compile(
    rf"(?:{'|'.join(VILLAGE_KEYWORDS)})[:\-]?\s*([A-Za-z0-9\s]+)", 
    re.IGNORECASE
)

# Tehsil
TEHSIL_KEYWORDS = [r"tehsil", r"taluk", r"sub\-division", r"taluka"]
TEHSIL_PATTERN = re.compile(
    rf"(?:{'|'.join(TEHSIL_KEYWORDS)})[:\-]?\s*([A-Za-z\s]+)", 
    re.IGNORECASE
)

# District
DISTRICT_KEYWORDS = [r"district", r"zila", r"dist"]
DISTRICT_PATTERN = re.compile(
    rf"(?:{'|'.join(DISTRICT_KEYWORDS)})[:\-]?\s*([A-Za-z\s]+)", 
    re.IGNORECASE
)
