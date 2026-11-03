import pytest
import pandas as pd
from backend.fairscan_core.auto_detect import auto_detect_audit_configuration
from backend.fairscan_core.ingestion import ingest_csv

def test_auto_detect_hiring():
    df = pd.DataFrame({
        "candidate_id": range(10),
        "gender": ["Male", "Female"] * 5,
        "education": ["BS", "MS"] * 5,
        "hired": [1, 0] * 5,
        "predicted_hire": [1, 1, 0, 0] * 2 + [1, 0]
    })
    meta = ingest_csv(df.to_csv(index=False).encode(), "test.csv")
    auto = auto_detect_audit_configuration(df, meta["columns"])
    
    assert auto["auto_target_col"] == "hired"
    assert str(auto["auto_favorable_outcome"]) == "1"
    assert "gender" in auto["auto_sensitive_cols"]
    assert auto["auto_prediction_col"] == "predicted_hire"
    assert auto["has_detected_configuration"] is True

def test_auto_detect_lending():
    df = pd.DataFrame({
        "applicant_id": range(10),
        "age_group": ["<25", "25-60"] * 5,
        "loan_approved": ["yes", "no"] * 5,
    })
    meta = ingest_csv(df.to_csv(index=False).encode(), "test_lending.csv")
    auto = auto_detect_audit_configuration(df, meta["columns"])
    
    assert auto["auto_target_col"] == "loan_approved"
    assert auto["auto_favorable_outcome"] == "yes"
    assert "age_group" in auto["auto_sensitive_cols"]

