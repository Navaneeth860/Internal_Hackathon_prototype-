import os
import json
import pytest
from backend.app.pipeline.document_pipeline import DocumentPipeline
from data.generate_test_docs import main as generate_docs

# Ensure mock documents are generated before running tests
@pytest.fixture(scope="module", autouse=True)
def setup_test_documents():
    print("Generating mock documents...")
    generate_docs()
    yield

def test_pipeline_document_a():
    """
    Test Document A: Clean, typed land record.
    Expected: High confidence and successful match against mock registry.
    """
    pipeline = DocumentPipeline()
    result = pipeline.process_document("data/samples/document_a.png")
    
    # Verify we got fields back
    fields_dict = {f.name: f for f in result.fields}
    
    # 1. Check owner name
    assert "owner_name" in fields_dict
    assert fields_dict["owner_name"].value == "Ramesh Kumar"
    assert fields_dict["owner_name"].status == "SUCCESS"
    assert fields_dict["owner_name"].confidence >= 0.8
    assert len(fields_dict["owner_name"].validation_warnings) == 0
    
    # 2. Check survey number
    assert "survey_number" in fields_dict
    assert fields_dict["survey_number"].value == "124/3"
    assert fields_dict["survey_number"].status == "SUCCESS"
    assert len(fields_dict["survey_number"].validation_warnings) == 0
    
    # 3. Check area
    assert "area" in fields_dict
    assert "2.45" in fields_dict["area"].value
    
    print("\n--- Document A Result JSON ---")
    print(result.model_dump_json(indent=2))

def test_pipeline_document_b():
    """
    Test Document B: Faded/Noisy scan.
    Expected: Extraction succeeds, but confidence could be slightly lower due to noise.
    """
    pipeline = DocumentPipeline()
    result = pipeline.process_document("data/samples/document_b.png")
    
    fields_dict = {f.name: f for f in result.fields}
    
    assert "owner_name" in fields_dict
    assert any(term in fields_dict["owner_name"].value for term in ["Ramesh", "Rmesh", "Rmesh", "mesh"])
    
    # Verification of coordinates presence
    for field in result.fields:
        if field.status == "SUCCESS":
            assert len(field.source_elements) > 0
            for element in field.source_elements:
                assert len(element.bbox) == 4

def test_pipeline_document_c():
    """
    Test Document C: Missing fields (Survey Number & Village).
    Expected: Validation triggers warning labels and sets status.
    """
    pipeline = DocumentPipeline()
    result = pipeline.process_document("data/samples/document_c.png")
    
    fields_dict = {f.name: f for f in result.fields}
    
    # Village check
    assert "village" in fields_dict
    assert fields_dict["village"].status == "MISSING"
    assert any("Required Field Warning" in w for w in fields_dict["village"].validation_warnings)
    
    # Survey number check
    assert "survey_number" in fields_dict
    assert fields_dict["survey_number"].status == "MISSING"
    assert any("Required Field Warning" in w for w in fields_dict["survey_number"].validation_warnings)

def test_pipeline_document_d():
    """
    Test Document D: Ambiguous/Conflicting owner record for survey 87.
    Expected: Validation warnings flag owner name discrepancy against government mock registry.
    """
    pipeline = DocumentPipeline()
    result = pipeline.process_document("data/samples/document_d.png")
    
    fields_dict = {f.name: f for f in result.fields}
    
    assert "survey_number" in fields_dict
    assert fields_dict["survey_number"].value == "87"
    
    # Should flag owner name conflict (Registry has 'Sunita Devi', Document has 'Ramesh Kumar')
    survey_warnings = fields_dict["survey_number"].validation_warnings
    assert any("Conflict" in w and "Sunita Devi" in w for w in survey_warnings)
    
    # Check that confidence engine penalized this field
    assert fields_dict["survey_number"].confidence < 0.8
    assert "conflicts" in fields_dict["survey_number"].explanation.lower()

def test_area_regex_false_positives():
    from backend.app.extraction import patterns
    
    # 1. Verify correct numeric matching on filler text
    match_ok = patterns.AREA_PATTERN.search("Area is recorded as 2.45 acres")
    assert match_ok is not None
    assert match_ok.group(1).strip() == "2.45 acres"
    
    # 2. Verify non-numeric strings do not trigger matches
    assert patterns.AREA_PATTERN.search("Area is empty") is None
    assert patterns.AREA_PATTERN.search("Area is recorded as acres") is None

if __name__ == "__main__":
    # If run directly, generate docs and execute the pipeline manually to output result files
    print("Running end-to-end pipeline test runner...")
    generate_docs()
    
    pipeline = DocumentPipeline()
    docs = ["document_a.png", "document_b.png", "document_c.png", "document_d.png"]
    
    os.makedirs("data/processed/json_outputs", exist_ok=True)
    
    for doc in docs:
        doc_path = os.path.join("data/samples", doc)
        print(f"\n==========================================")
        print(f"Processing {doc_path}...")
        try:
            result = pipeline.process_document(doc_path)
            output_json_path = os.path.join("data/processed/json_outputs", doc.replace(".png", "_result.json"))
            with open(output_json_path, "w") as f:
                json.dump(result.model_dump(), f, indent=2)
            print(f"Extraction successful! Output saved to: {output_json_path}")
            
            # Print brief summary
            print("\nExtracted Fields Summary:")
            for field in result.fields:
                val = field.value or "<MISSING>"
                warns = f" [! {len(field.validation_warnings)} warnings]" if field.validation_warnings else ""
                print(f" - {field.name:15}: {val:15} | Conf: {int(field.confidence * 100)}% | Status: {field.status}{warns}")
                for w in field.validation_warnings:
                    print(f"    * Warning: {w}")
        except Exception as e:
            print(f"Failed to process {doc}: {e}")
            import traceback
            traceback.print_exc()
