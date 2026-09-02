import logging
import re
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
        Clears old warnings before re-running to avoid stale logs.
        """
        fields = extraction_result.fields
        
        # 1. Clear old warnings
        for f in fields:
            f.validation_warnings = []
            
        # Helper maps to quickly lookup extracted fields
        fields_map = {f.name: f for f in fields}
        
        owner_field = fields_map.get("owner_name") or fields_map.get("seller_name")
        survey_field = fields_map.get("survey_number")
        area_field = fields_map.get("area") or fields_map.get("total_area")
        village_field = fields_map.get("village") or fields_map.get("property_location")
        
        # 2. Required field checks (universal standard fields)
        if owner_field and owner_field.status in ["MISSING", "NOT_PRESENT"]:
            owner_field.validation_warnings.append(f"Required Field Warning: Field '{owner_field.name}' is missing but is mandatory for land records.")
            owner_field.status = "MISSING"

        for name in ["survey_number", "village"]:
            f = fields_map.get(name)
            if f and f.status in ["MISSING", "NOT_PRESENT"]:
                f.validation_warnings.append(f"Required Field Warning: Field '{f.name}' is missing but is mandatory for land records.")
                f.status = "MISSING"


        # 3. Format validation (universal)
        if survey_field and survey_field.value:
            survey_warns = rules.validate_survey_format(survey_field.value)
            survey_field.validation_warnings.extend(survey_warns)
            
        if area_field and area_field.value:
            area_warns = rules.validate_area_unit(area_field.value)
            area_field.validation_warnings.extend(area_warns)

        # 4. Cross-reference registry verification (Bhulekh / land registry simulation)
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

        # 5. Subdivision Area Logical Warning Rule (universal)
        if survey_field and survey_field.value and area_field and area_field.value:
            subdiv_warns = rules.validate_subdivision_area(survey_field.value, area_field.value)
            area_field.validation_warnings.extend(subdiv_warns)
            
        # 6. Sale Deed Specific Validations
        if extraction_result.document_subtype == "Sale Deed":
            seller = fields_map.get("seller_name")
            buyer = fields_map.get("buyer_name")
            doc_date = fields_map.get("document_date")
            consideration = fields_map.get("sale_consideration")
            
            seller_val = seller.value if seller else None
            buyer_val = buyer.value if buyer else None
            doc_date_val = doc_date.value if doc_date else None
            consideration_val = consideration.value if consideration else None
            
            deed_warns = rules.validate_sale_deed(seller_val, buyer_val, doc_date_val, consideration_val)
            for warn in deed_warns:
                if "identical" in warn:
                    if seller: seller.validation_warnings.append(warn)
                    if buyer: buyer.validation_warnings.append(warn)
                elif "date" in warn:
                    if doc_date: doc_date.validation_warnings.append(warn)
                elif "consideration" in warn or "monetary" in warn:
                    if consideration: consideration.validation_warnings.append(warn)
                    
        # 7. Partition Deed Specific Validations
        elif extraction_result.document_subtype == "Partition Deed":
            parties = fields_map.get("parties")
            party_count = fields_map.get("party_count")
            total_area = fields_map.get("total_area")
            share_allocation = fields_map.get("share_allocation")
            
            parties_val = parties.value if parties else None
            party_count_val = party_count.value if party_count else None
            total_area_val = total_area.value if total_area else None
            share_allocation_val = share_allocation.value if share_allocation else None
            
            deed_warns = rules.validate_partition_deed(parties_val, party_count_val, total_area_val, share_allocation_val)
            for warn in deed_warns:
                if "at least two" in warn:
                    if parties: parties.validation_warnings.append(warn)
                elif "Party count" in warn or "listed parties" in warn:
                    if party_count: party_count.validation_warnings.append(warn)
                elif "Total area" in warn or "allocated shares" in warn or "allocations" in warn:
                    if share_allocation: share_allocation.validation_warnings.append(warn)
                    if total_area: total_area.validation_warnings.append(warn)
                    
        # 8. Log validation results
        total_warnings = sum(len(f.validation_warnings) for f in fields)
        logger.info(f"Validation completed. Found {total_warnings} total warning flags.")
        
        return extraction_result
