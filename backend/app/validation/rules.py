import re
from typing import Dict, Any, List, Optional

# Mock Land Record database to represent the "government registry"
# Structure: { survey_number: { "owner": name, "village": village, "area_acres": area } }
MOCK_REGISTRY_DATABASE: Dict[str, Dict[str, Any]] = {
    "124/3": {
        "owner": "Ramesh Kumar",
        "village": "Rampur",
        "area_acres": 2.45
    },
    "124-A": {
        "owner": "Suresh Chandra",
        "village": "Rampur",
        "area_acres": 1.25
    },
    "87": {
        "owner": "Sunita Devi",
        "village": "Kalyanpur",
        "area_acres": 3.10
    },
    "45/2B": {
        "owner": "Amit Singh",
        "village": "Gopalpur",
        "area_acres": 0.75
    }
}

# Regex to validate standard survey number formats (e.g., 124/3, 124-A, 87, 45/2B)
SURVEY_FORMAT_REGEX = re.compile(r"^\d+(?:[\/\-][A-Za-z0-9]+)?$")

# Helper to normalize owner names for comparison (lowercase, remove spaces and dots)
def normalize_string(val: Optional[str]) -> str:
    if not val:
        return ""
    return re.sub(r"[^a-z0-9]", "", val.lower())

def validate_survey_format(value: str) -> List[str]:
    """
    Validates if the survey number format is standard.
    """
    warnings = []
    cleaned_value = value.strip().replace(" ", "")
    if not SURVEY_FORMAT_REGEX.match(cleaned_value):
        warnings.append(f"Format Warning: Survey number '{value}' does not match standard patterns (e.g. 124/3 or 124-A).")
    return warnings

def validate_area_unit(value: str) -> List[str]:
    """
    Validates if the area contains a recognized land area unit.
    """
    warnings = []
    value_lower = value.lower()
    valid_units = ["acre", "acres", "hectare", "hectares", "hec", "bigha", "bighas", "sq", "sqft", "sqm"]
    
    # Check if any valid unit string exists in the text
    if not any(unit in value_lower for unit in valid_units):
        warnings.append(f"Format Warning: Area field '{value}' lacks standard units (Acres, Hectares, Bighas).")
        
    # Extract numerical part and check sanity
    numbers = re.findall(r"\d+(?:\.\d+)?", value)
    if not numbers:
        warnings.append("Format Warning: Area field contains no readable numerical value.")
    else:
        try:
            val_float = float(numbers[0])
            if val_float <= 0:
                warnings.append("Plausibility Warning: Area value cannot be zero or negative.")
            elif val_float > 500:
                warnings.append(f"Plausibility Warning: Extremely large area detected ({val_float}). Please double check.")
        except ValueError:
            warnings.append("Plausibility Warning: Failed to parse numerical value from Area.")
            
    return warnings

def cross_reference_mock_database(
    survey_no: Optional[str], 
    owner_name: Optional[str], 
    village: Optional[str]
) -> List[str]:
    """
    Cross-references extracted data with the mock registry database.
    This simulates backend integration with state land record repositories (e.g., Bhulekh).
    """
    warnings = []
    if not survey_no:
        return warnings
        
    cleaned_survey = survey_no.strip().replace(" ", "")
    
    # Find matching record in mock database
    matched_record = None
    for s_key, data in MOCK_REGISTRY_DATABASE.items():
        if normalize_string(s_key) == normalize_string(cleaned_survey):
            matched_record = data
            break
            
    if not matched_record:
        warnings.append(
            f"Mock Verification: Survey number '{survey_no}' was not found in the official registry mock database."
        )
        return warnings
        
    # Check Owner Name consistency
    if owner_name:
        reg_owner = matched_record["owner"]
        if normalize_string(reg_owner) != normalize_string(owner_name):
            # Check for partial match/subset
            n_reg = normalize_string(reg_owner)
            n_ext = normalize_string(owner_name)
            if n_reg not in n_ext and n_ext not in n_reg:
                warnings.append(
                    f"Mock Verification Conflict: Extracted Owner '{owner_name}' does not match registered owner '{reg_owner}' for survey '{survey_no}'."
                )
                
    # Check Village consistency
    if village:
        reg_village = matched_record["village"]
        if normalize_string(reg_village) != normalize_string(village):
            warnings.append(
                f"Mock Verification Conflict: Extracted Village '{village}' does not match registered location '{reg_village}' for survey '{survey_no}'."
            )
            
    return warnings
