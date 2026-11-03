from fastapi.testclient import TestClient
from backend.api.main import app
import pandas as pd
import io

client = TestClient(app)

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_api_load_sample():
    response = client.post("/api/load-sample?sample_name=hiring")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "tech_recruitment_sample.csv"
    assert data["total_rows"] > 0
    assert len(data["fingerprint"]) == 64

def test_api_profile_and_audit():
    # Load sample first
    load_resp = client.post("/api/load-sample?sample_name=hiring")
    fp = load_resp.json()["fingerprint"]

    # Profile
    prof_resp = client.post("/api/profile", json={
        "fingerprint": fp,
        "target_col": "hired",
        "favorable_outcome": 1,
        "sensitive_cols": ["gender"]
    })
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert "target_profile" in prof_data
    assert "sensitive_profiles" in prof_data

    # Audit
    audit_resp = client.post("/api/audit", json={
        "fingerprint": fp,
        "target_col": "hired",
        "favorable_outcome": 1,
        "sensitive_cols": ["gender"],
        "reference_groups": {"gender": "Male"},
        "prediction_col": "predicted_hire"
    })
    assert audit_resp.status_code == 200
    audit_res = audit_resp.json()
    assert "audit_results" in audit_res
    assert "findings" in audit_res
    assert "explanation" in audit_res

    # PDF Report Download
    report_resp = client.get("/api/report/pdf")
    assert report_resp.status_code == 200
    assert report_resp.headers["content-type"] == "application/pdf"
    assert len(report_resp.content) > 1000

def test_api_reweighting():
    # Reweight
    client.post("/api/load-sample?sample_name=hiring")
    reweight_resp = client.post("/api/reweight", json={
        "target_col": "hired",
        "favorable_outcome": 1,
        "sensitive_col": "gender",
        "reference_group": "Male"
    })
    assert reweight_resp.status_code == 200
    reweight_data = reweight_resp.json()
    assert "before_metrics" in reweight_data
    assert "after_metrics" in reweight_data

    # Download CSV
    dl_resp = client.get("/api/download-reweighted?sensitive_col=gender&reference_group=Male&target_col=hired&favorable_outcome=1")
    assert dl_resp.status_code == 200
    assert "sample_weight" in dl_resp.text

