import pytest
import pandas as pd
import numpy as np

from backend.fairscan_core.ingestion import ingest_csv, profile_selected_variables, DatasetIngestionError
from backend.fairscan_core.metrics import (
    compute_group_selection_rates,
    calculate_statistical_parity,
    calculate_disparate_impact,
    calculate_model_fairness_metrics,
    run_full_dataset_audit,
    FairnessCalculationError,
)
from backend.fairscan_core.mitigation import apply_dataset_reweighting
from backend.fairscan_core.findings import generate_deterministic_findings
from backend.fairscan_core.report import generate_pdf_audit_report


@pytest.fixture
def sample_hiring_csv_bytes():
    """Generates synthetic hiring dataset with known disparities."""
    # Group A: 100 rows, 80 hired (80%)
    # Group B: 100 rows, 40 hired (40%) -> Disparate Impact = 0.50, Parity Diff = -0.40
    data = []
    for _ in range(80):
        data.append({"gender": "Male", "hired": 1, "predicted": 1})
    for _ in range(20):
        data.append({"gender": "Male", "hired": 0, "predicted": 0})
    for _ in range(40):
        data.append({"gender": "Female", "hired": 1, "predicted": 1})
    for _ in range(60):
        data.append({"gender": "Female", "hired": 0, "predicted": 0})

    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode("utf-8")


def test_csv_ingestion_success(sample_hiring_csv_bytes):
    result = ingest_csv(sample_hiring_csv_bytes, "hiring.csv")
    assert result["total_rows"] == 200
    assert result["total_columns"] == 3
    assert result["filename"] == "hiring.csv"
    assert len(result["fingerprint"]) == 64
    assert len(result["preview_rows"]) == 50


def test_csv_ingestion_empty_file():
    with pytest.raises(DatasetIngestionError, match="empty"):
        ingest_csv(b"", "empty.csv")


def test_csv_ingestion_single_column():
    csv_bytes = b"single_column\nval1\nval2\n"
    with pytest.raises(DatasetIngestionError, match="at least 2 columns"):
        ingest_csv(csv_bytes, "single.csv")


def test_csv_ingestion_duplicate_columns():
    csv_bytes = b"col1,col1,col2\n1,2,3\n"
    with pytest.raises(DatasetIngestionError, match="Duplicate column headers"):
        ingest_csv(csv_bytes, "duplicate.csv")


def test_group_selection_rates():
    df = pd.DataFrame({
        "gender": ["Male"] * 10 + ["Female"] * 10,
        "hired": [1] * 8 + [0] * 2 + [1] * 4 + [0] * 6,
    })
    rates = compute_group_selection_rates(df, target_col="hired", favorable_outcome=1, sensitive_col="gender")
    assert rates["Male"]["selection_rate"] == 0.8
    assert rates["Male"]["favorable_count"] == 8
    assert rates["Male"]["total_count"] == 10
    assert rates["Female"]["selection_rate"] == 0.4
    assert rates["Female"]["favorable_count"] == 4
    assert rates["Female"]["total_count"] == 10


def test_statistical_parity_and_disparate_impact():
    stats_data = {
        "Male": {"selection_rate": 0.8, "total_count": 100, "favorable_count": 80, "selection_rate_pct": 80.0},
        "Female": {"selection_rate": 0.4, "total_count": 100, "favorable_count": 40, "selection_rate_pct": 40.0},
    }
    spd = calculate_statistical_parity(stats_data, reference_group="Male")
    assert spd["comparisons"]["Female"]["difference"] == -0.4
    assert spd["comparisons"]["Male"]["difference"] == 0.0

    di = calculate_disparate_impact(stats_data, reference_group="Male")
    assert di["comparisons"]["Female"]["ratio"] == 0.5
    assert di["comparisons"]["Female"]["violates_80_rule"] is True
    assert di["comparisons"]["Male"]["ratio"] == 1.0


def test_disparate_impact_zero_denominator():
    stats_data = {
        "Ref": {"selection_rate": 0.0, "total_count": 50, "favorable_count": 0, "selection_rate_pct": 0.0},
        "Comp": {"selection_rate": 0.2, "total_count": 50, "favorable_count": 10, "selection_rate_pct": 20.0},
    }
    di = calculate_disparate_impact(stats_data, reference_group="Ref")
    assert di["comparisons"]["Comp"]["zero_denominator"] is True
    assert di["comparisons"]["Comp"]["ratio"] is None
    assert di["comparisons"]["Comp"]["status"] == "inapplicable"


def test_single_group_attribute():
    df = pd.DataFrame({
        "gender": ["AllMale"] * 50,
        "hired": [1] * 25 + [0] * 25,
    })
    audit = run_full_dataset_audit(df, "hired", 1, ["gender"], {"gender": "AllMale"})
    assert audit["attribute_audits"]["gender"]["status"] == "inapplicable"


def test_model_metrics_without_prediction():
    df = pd.DataFrame({"gender": ["A", "B"], "hired": [1, 0]})
    res = calculate_model_fairness_metrics(df, "hired", None, 1, "gender", "A")
    assert res["status"] == "unavailable"


def test_model_metrics_with_valid_prediction():
    df = pd.DataFrame({
        "gender": ["A"] * 20 + ["B"] * 20,
        "y_true": [1] * 10 + [0] * 10 + [1] * 10 + [0] * 10,
        "y_pred": [1] * 9 + [0] * 11 + [1] * 5 + [0] * 15,
    })
    res = calculate_model_fairness_metrics(df, "y_true", "y_pred", 1, "gender", "A")
    assert res["status"] == "available"
    assert "equal_opportunity" in res
    assert "equalized_odds" in res


def test_kamiran_calders_reweighting():
    df = pd.DataFrame({
        "gender": ["Male"] * 50 + ["Female"] * 50,
        "hired": [1] * 40 + [0] * 10 + [1] * 20 + [0] * 30,
    })
    reweighted = apply_dataset_reweighting(df, "hired", 1, "gender", "Male")
    assert "weight_multipliers" in reweighted
    # In reweighted distribution, selection rates equalize
    after_male = reweighted["after_metrics"]["group_stats"]["Male"]["selection_rate"]
    after_female = reweighted["after_metrics"]["group_stats"]["Female"]["selection_rate"]
    assert abs(after_male - after_female) < 0.01


def test_findings_and_pdf_generation(sample_hiring_csv_bytes):
    meta = ingest_csv(sample_hiring_csv_bytes, "hiring_audit.csv")
    df = pd.read_csv(io_bytes := io_from_bytes(sample_hiring_csv_bytes))
    profile = profile_selected_variables(df, "hired", 1, ["gender"])
    audit = run_full_dataset_audit(df, "hired", 1, ["gender"], {"gender": "Male"})
    findings = generate_deterministic_findings(audit, profile)

    assert findings["adverse_impact_count"] >= 1
    assert len(findings["investigation_recommendations"]) >= 1

    pdf_bytes = generate_pdf_audit_report(meta, audit, findings, "Test explanation")
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def io_from_bytes(b):
    import io
    return io.BytesIO(b)

