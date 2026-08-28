import logging
from typing import List
from backend.app.extraction.schemas import ExtractionResult, ExtractedField
from backend.app.validation import rules

logger = logging.getLogger(__name__)

class Validator:
    """
    Validator executes validation checks, format audits, and mock government registry
    cross-referencing. It modifies fields in-place to append validation warnings.
    """
    
    def __init__(self):
        pass

    def validate(self, extraction_result: ExtractionResult) -> ExtractionResult:
        """
        Executes validation on the extraction result and appends warning messages.
        """
        fields = extraction_result.fields
        
        # Helper maps to quickly lookup extracted values
        owner_field = next((f for f in fields if f.name == "owner_name"), None)
        survey_field = next((f for f in fields if f.name == "survey_number"), None)
        area_field = next((f for f in fields if f.name == "area"), None)
        village_field = next((f for f in fields if f.name == "village"), None)
        
        # 1. Required field checks
        required_fields = ["owner_name", "survey_number", "village"]
        for f in fields:
            if f.name in required_fields and f.status in ["MISSING", "NOT_PRESENT"]:
                f.validation_warnings.append(f"Required Field Warning: Field '{f.name}' is missing but is mandatory for land records.")
                f.status = "MISSING"

        # 2. Format validation
        if survey_field and survey_field.value:
            survey_warns = rules.validate_survey_format(survey_field.value)
            survey_field.validation_warnings.extend(survey_warns)
            
        if area_field and area_field.value:
            area_warns = rules.validate_area_unit(area_field.value)
            area_field.validation_warnings.extend(area_warns)

        # 3. Cross-reference registry verification (Bhulekh / land registry simulation)
        survey_val = survey_field.value if survey_field else None
        owner_val = owner_field.value if owner_field else None
        village_val = village_field.value if village_field else None
        
        if survey_val:
            registry_warnings = rules.cross_reference_mock_database(
                survey_no=survey_val,
                owner_name=owner_val,
                village=village_val
            )
            # If there's a database mismatch or record missing, associate warnings with the survey number
            if registry_warnings and survey_field:
                survey_field.validation_warnings.extend(registry_warnings)
                
        # 4. Log validation results
        total_warnings = sum(len(f.validation_warnings) for f in fields)
        logger.info(f"Validation completed. Found {total_warnings} total warning flags.")
        
        return extraction_result
