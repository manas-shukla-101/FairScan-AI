import os
import io
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.fairscan_core.ingestion import ingest_csv, profile_selected_variables, DatasetIngestionError
from backend.fairscan_core.metrics import run_full_dataset_audit, FairnessCalculationError
from backend.fairscan_core.findings import generate_deterministic_findings
from backend.fairscan_core.mitigation import apply_dataset_reweighting
from backend.fairscan_core.explainer import generate_audit_explanation
from backend.fairscan_core.report import generate_pdf_audit_report
from backend.fairscan_core.auto_detect import auto_detect_audit_configuration

app = FastAPI(
    title="FairScan API",
    description="Dataset Fairness & Bias Audit Engine API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store keyed by dataset fingerprint (or active dataset)
DATASET_STORE: Dict[str, Dict[str, Any]] = {}
LATEST_FINGERPRINT: Optional[str] = None


class ProfileRequest(BaseModel):
    fingerprint: Optional[str] = None
    target_col: str
    favorable_outcome: Any
    sensitive_cols: List[str]


class AuditRequest(BaseModel):
    fingerprint: Optional[str] = None
    target_col: str
    favorable_outcome: Any
    sensitive_cols: List[str]
    reference_groups: Dict[str, str]
    prediction_col: Optional[str] = None
    llm_provider: Optional[str] = "auto"  # auto, groq, gemini, deterministic
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class ReweightRequest(BaseModel):
    fingerprint: Optional[str] = None
    target_col: str
    favorable_outcome: Any
    sensitive_col: str
    reference_group: str


@app.get("/")
def root():
    return {
        "app": "FairScan API",
        "status": "online",
        "version": "1.0.0",
        "disclaimer": "FairScan is an analytical support tool. It does not certify legal compliance or prove discrimination.",
    }


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global LATEST_FINGERPRINT
    contents = await file.read()
    try:
        metadata = ingest_csv(contents, filename=file.filename or "dataset.csv")
        df = pd.read_csv(io.BytesIO(contents))
        fp = metadata["fingerprint"]

        # Run intelligent automatic variable discovery
        auto_config = auto_detect_audit_configuration(df, metadata["columns"])
        metadata["auto_config"] = auto_config

        DATASET_STORE[fp] = {
            "df": df,
            "bytes": contents,
            "metadata": metadata,
            "auto_config": auto_config,
            "last_audit": None,
            "last_findings": None,
            "last_explanation": None,
        }
        LATEST_FINGERPRINT = fp
        return sanitize_for_json(metadata)
    except DatasetIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error processing dataset: {str(e)}")


@app.post("/api/auto-audit")
async def run_automatic_end_to_end_audit(
    file: Optional[UploadFile] = File(None),
    sample_name: Optional[str] = None,
    x_groq_api_key: Optional[str] = Header(None, alias="x-groq-api-key"),
    x_gemini_api_key: Optional[str] = Header(None, alias="x-gemini-api-key"),
    x_llm_provider: Optional[str] = Header(None, alias="x-llm-provider"),
):
    """
    1-Click Zero-Intervention Pipeline:
    Uploads dataset -> Auto-detects variables -> Runs full fairness audit -> Produces findings, mitigations, and report.
    """
    global LATEST_FINGERPRINT

    if file:
        contents = await file.read()
        fname = file.filename or "dataset.csv"
        df = pd.read_csv(io.BytesIO(contents))
    elif sample_name:
        if sample_name == "hiring":
            data = []
            for _ in range(120):
                data.append({"gender": "Male", "education": "Bachelors", "hired": 1, "predicted_hire": 1})
            for _ in range(30):
                data.append({"gender": "Male", "education": "Bachelors", "hired": 0, "predicted_hire": 0})
            for _ in range(45):
                data.append({"gender": "Female", "education": "Bachelors", "hired": 1, "predicted_hire": 1})
            for _ in range(75):
                data.append({"gender": "Female", "education": "Bachelors", "hired": 0, "predicted_hire": 0})
            df = pd.DataFrame(data)
            fname = "tech_recruitment_sample.csv"
        else:
            data = []
            for _ in range(150):
                data.append({"age_group": "25-60", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
            for _ in range(50):
                data.append({"age_group": "25-60", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
            for _ in range(35):
                data.append({"age_group": "<25", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
            for _ in range(65):
                data.append({"age_group": "<25", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
            for _ in range(40):
                data.append({"age_group": ">60", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
            for _ in range(60):
                data.append({"age_group": ">60", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
            df = pd.DataFrame(data)
            fname = "credit_approval_sample.csv"
        contents = df.to_csv(index=False).encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file upload or a sample_name.")

    try:
        metadata = ingest_csv(contents, filename=fname)
        fp = metadata["fingerprint"]

        # 1. Automatic Discovery
        auto_config = auto_detect_audit_configuration(df, metadata["columns"])
        target_col = auto_config["auto_target_col"]
        fav_val = auto_config["auto_favorable_outcome"]
        sensitive_cols = auto_config["auto_sensitive_cols"]
        ref_groups = auto_config["auto_reference_groups"]
        pred_col = auto_config["auto_prediction_col"]

        if not target_col or not sensitive_cols:
            raise DatasetIngestionError("Could not auto-identify target or sensitive columns. Please verify tabular format.")

        # 2. Dataset Profiling
        profile = profile_selected_variables(
            df=df,
            target_col=target_col,
            favorable_outcome=fav_val,
            sensitive_cols=sensitive_cols,
        )

        # 3. Fairness Audit Calculations
        audit_results = run_full_dataset_audit(
            df=df,
            target_col=target_col,
            favorable_outcome=fav_val,
            sensitive_cols=sensitive_cols,
            reference_groups=ref_groups,
            prediction_col=pred_col,
        )

        # 4. Deterministic Findings & LLM Explanations
        findings = generate_deterministic_findings(audit_results, profile)
        explanation = generate_audit_explanation(
            audit_results=audit_results,
            findings=findings,
            llm_provider=x_llm_provider or "auto",
            groq_api_key=x_groq_api_key,
            gemini_api_key=x_gemini_api_key,
        )

        # 5. Auto-compute Mitigation for the primary sensitive attribute
        mitigation_data = None
        if sensitive_cols:
            primary_sensitive = sensitive_cols[0]
            primary_ref = ref_groups.get(primary_sensitive, str(df[primary_sensitive].dropna().unique()[0]))
            reweighted = apply_dataset_reweighting(
                df=df,
                target_col=target_col,
                favorable_outcome=fav_val,
                sensitive_col=primary_sensitive,
                reference_group=primary_ref,
            )
            mitigation_data = {k: v for k, v in reweighted.items() if k != "reweighted_csv_string"}

        # Store session
        metadata["auto_config"] = auto_config
        DATASET_STORE[fp] = {
            "df": df,
            "bytes": contents,
            "metadata": metadata,
            "auto_config": auto_config,
            "last_audit": audit_results,
            "last_findings": findings,
            "last_explanation": explanation,
            "last_profile": profile,
            "last_mitigation": mitigation_data,
        }
        LATEST_FINGERPRINT = fp

        return sanitize_for_json({
            "status": "success",
            "dataset_metadata": metadata,
            "auto_config": auto_config,
            "profile": profile,
            "audit_results": audit_results,
            "findings": findings,
            "explanation": explanation,
            "mitigation": mitigation_data,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/load-sample")
async def load_sample_dataset(sample_name: str = "lending"):
    global LATEST_FINGERPRINT
    # Generates standard benchmark datasets
    if sample_name == "hiring":
        data = []
        for _ in range(120):
            data.append({"gender": "Male", "education": "Bachelors", "hired": 1, "predicted_hire": 1})
        for _ in range(30):
            data.append({"gender": "Male", "education": "Bachelors", "hired": 0, "predicted_hire": 0})
        for _ in range(45):
            data.append({"gender": "Female", "education": "Bachelors", "hired": 1, "predicted_hire": 1})
        for _ in range(75):
            data.append({"gender": "Female", "education": "Bachelors", "hired": 0, "predicted_hire": 0})
        df = pd.DataFrame(data)
        fname = "tech_recruitment_sample.csv"
    else:
        # Lending benchmark
        data = []
        for _ in range(150):
            data.append({"age_group": "25-60", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
        for _ in range(50):
            data.append({"age_group": "25-60", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
        for _ in range(35):
            data.append({"age_group": "<25", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
        for _ in range(65):
            data.append({"age_group": "<25", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
        for _ in range(40):
            data.append({"age_group": ">60", "income_level": "Medium", "loan_approved": 1, "model_prediction": 1})
        for _ in range(60):
            data.append({"age_group": ">60", "income_level": "Medium", "loan_approved": 0, "model_prediction": 0})
        df = pd.DataFrame(data)
        fname = "credit_approval_sample.csv"

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    metadata = ingest_csv(csv_bytes, filename=fname)
    fp = metadata["fingerprint"]
    DATASET_STORE[fp] = {
        "df": df,
        "bytes": csv_bytes,
        "metadata": metadata,
        "last_audit": None,
        "last_findings": None,
        "last_explanation": None,
    }
    LATEST_FINGERPRINT = fp
    return metadata


def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts numpy primitives to native python types."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif pd.isna(obj):
        return None
    return obj


@app.post("/api/profile")
def profile_dataset(req: ProfileRequest):
    fp = req.fingerprint or LATEST_FINGERPRINT
    if not fp or fp not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="No active dataset found. Please upload a dataset first.")

    df = DATASET_STORE[fp]["df"]
    try:
        profile = profile_selected_variables(
            df=df,
            target_col=req.target_col,
            favorable_outcome=req.favorable_outcome,
            sensitive_cols=req.sensitive_cols,
        )
        return sanitize_for_json(profile)
    except DatasetIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/audit")
def perform_audit(req: AuditRequest):
    fp = req.fingerprint or LATEST_FINGERPRINT
    if not fp or fp not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="No active dataset found.")

    record = DATASET_STORE[fp]
    df = record["df"]

    try:
        profile = profile_selected_variables(
            df=df,
            target_col=req.target_col,
            favorable_outcome=req.favorable_outcome,
            sensitive_cols=req.sensitive_cols,
        )
        audit_results = run_full_dataset_audit(
            df=df,
            target_col=req.target_col,
            favorable_outcome=req.favorable_outcome,
            sensitive_cols=req.sensitive_cols,
            reference_groups=req.reference_groups,
            prediction_col=req.prediction_col,
        )
        findings = generate_deterministic_findings(audit_results, profile)
        explanation = generate_audit_explanation(
            audit_results=audit_results,
            findings=findings,
            llm_provider=req.llm_provider or "auto",
            groq_api_key=req.groq_api_key,
            gemini_api_key=req.gemini_api_key,
        )

        # Cache results in session store
        record["last_audit"] = audit_results
        record["last_findings"] = findings
        record["last_explanation"] = explanation

        return sanitize_for_json({
            "dataset_metadata": record["metadata"],
            "profile": profile,
            "audit_results": audit_results,
            "findings": findings,
            "explanation": explanation,
        })
    except FairnessCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}")


@app.post("/api/reweight")
def reweight_dataset(req: ReweightRequest):
    fp = req.fingerprint or LATEST_FINGERPRINT
    if not fp or fp not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="No active dataset found.")

    df = DATASET_STORE[fp]["df"]
    try:
        reweighted_data = apply_dataset_reweighting(
            df=df,
            target_col=req.target_col,
            favorable_outcome=req.favorable_outcome,
            sensitive_col=req.sensitive_col,
            reference_group=req.reference_group,
        )
        resp = {k: v for k, v in reweighted_data.items() if k != "reweighted_csv_string"}
        return sanitize_for_json(resp)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download-reweighted")
def download_reweighted_csv(sensitive_col: str, reference_group: str, target_col: str, favorable_outcome: str):
    fp = LATEST_FINGERPRINT
    if not fp or fp not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="No active dataset found.")

    df = DATASET_STORE[fp]["df"]
    reweighted = apply_dataset_reweighting(df, target_col, favorable_outcome, sensitive_col, reference_group)
    csv_data = reweighted["reweighted_csv_string"]

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fairscan_reweighted_{sensitive_col}.csv"},
    )


@app.get("/api/report/pdf")
def download_report_pdf():
    fp = LATEST_FINGERPRINT
    if not fp or fp not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="No active audit found. Run an audit first.")

    rec = DATASET_STORE[fp]
    if not rec["last_audit"] or not rec["last_findings"]:
        raise HTTPException(status_code=400, detail="Audit has not been run yet for this dataset.")

    pdf_bytes = generate_pdf_audit_report(
        dataset_meta=rec["metadata"],
        audit_results=rec["last_audit"],
        findings=rec["last_findings"],
        explanation_text=rec["last_explanation"]["explanation_text"] if rec["last_explanation"] else "",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fairscan_audit_report.pdf"},
    )


@app.post("/api/reset")
def reset_session():
    global LATEST_FINGERPRINT
    DATASET_STORE.clear()
    LATEST_FINGERPRINT = None
    return {"status": "success", "message": "FairScan session reset."}
