import hashlib
import io
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class DatasetIngestionError(Exception):
    """Custom exception raised for dataset loading and schema validation errors."""
    pass


def compute_dataset_hash(file_bytes: bytes) -> str:
    """Compute a deterministic SHA-256 fingerprint of the dataset bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def ingest_csv(file_bytes: bytes, filename: str = "dataset.csv") -> Dict[str, Any]:
    """
    Ingest, validate, and extract initial metadata from CSV bytes without modifying or discarding rows.
    """
    if not file_bytes or len(file_bytes.strip()) == 0:
        raise DatasetIngestionError("The uploaded CSV file is empty. Please provide a file with valid tabular data.")

    try:
        # First read the header line directly to check for duplicate column names
        header_line = file_bytes.splitlines()[0].decode("utf-8", errors="replace")
        header_tokens = [col.strip() for col in header_line.split(",")]
        token_counts = pd.Series(header_tokens).value_counts()
        duplicate_headers = token_counts[token_counts > 1].index.tolist()
        if duplicate_headers:
            raise DatasetIngestionError(f"Duplicate column headers detected: {duplicate_headers}. Headers must be distinct.")

        # Try UTF-8 first, fallback to latin-1
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    except DatasetIngestionError:
        raise
    except Exception as e:
        raise DatasetIngestionError(f"Failed to parse CSV file: {str(e)}")

    if df.empty:
        raise DatasetIngestionError("The parsed dataset contains 0 rows.")

    if len(df.columns) < 2:
        raise DatasetIngestionError(
            f"The dataset must contain at least 2 columns (target variable and at least one sensitive attribute). Found: {len(df.columns)}"
        )

    # Check for duplicate column names in header
    col_counts = pd.Series(df.columns).value_counts()
    duplicate_cols = col_counts[col_counts > 1].index.tolist()
    if duplicate_cols:
        raise DatasetIngestionError(f"Duplicate column headers detected: {duplicate_cols}. Headers must be distinct.")

    # Profiling columns
    columns_info: List[Dict[str, Any]] = []
    for col in df.columns:
        series = df[col]
        non_null_count = int(series.notna().sum())
        null_count = int(series.isna().sum())
        null_pct = float(round((null_count / len(df)) * 100, 2))
        unique_vals = int(series.nunique(dropna=True))

        # Detect data type
        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_bool = pd.api.types.is_bool_dtype(series)
        dtype_str = str(series.dtype)

        # Classify as categorical candidate or numeric candidate
        if is_bool or unique_vals <= 10 or not is_numeric:
            type_category = "categorical"
        else:
            type_category = "continuous"

        # Unique sample values (up to 10)
        sample_uniques = [
            val.item() if hasattr(val, "item") else val
            for val in series.dropna().unique()[:10]
        ]
        # Convert non-serializable objects to string
        sample_uniques = [
            str(x) if isinstance(x, (pd.Timestamp, np.generic)) else x
            for x in sample_uniques
        ]

        columns_info.append({
            "name": str(col),
            "dtype": dtype_str,
            "type_category": type_category,
            "non_null_count": non_null_count,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": unique_vals,
            "sample_values": sample_uniques,
            "is_binary": bool(unique_vals == 2),
        })

    # Prepare preview (top 50 rows, JSON-serializable)
    preview_df = df.head(50).copy()
    # Replace NaN/inf with None for clean JSON serialization
    preview_records = preview_df.replace({np.nan: None}).to_dict(orient="records")

    fingerprint = compute_dataset_hash(file_bytes)

    return {
        "filename": filename,
        "fingerprint": fingerprint,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": columns_info,
        "preview_rows": preview_records,
        "missing_total_cells": int(df.isna().sum().sum()),
        "has_missing_values": bool(df.isna().sum().sum() > 0),
    }


def profile_selected_variables(
    df: pd.DataFrame,
    target_col: str,
    favorable_outcome: Any,
    sensitive_cols: List[str],
) -> Dict[str, Any]:
    """
    Profile dataset outcome distribution and sensitive attribute group representations.
    Does NOT mutate original DataFrame.
    """
    if target_col not in df.columns:
        raise DatasetIngestionError(f"Target column '{target_col}' not found in dataset.")

    for col in sensitive_cols:
        if col not in df.columns:
            raise DatasetIngestionError(f"Sensitive column '{col}' not found in dataset.")

    total_rows = len(df)
    target_series = df[target_col]

    # Convert favorable_outcome to matching dtype comparison if possible
    # e.g., if favorable_outcome is "1" and target is integer 1
    def matches_favorable(val):
        if pd.isna(val):
            return False
        if str(val).strip().lower() == str(favorable_outcome).strip().lower():
            return True
        try:
            if float(val) == float(favorable_outcome):
                return True
        except (ValueError, TypeError):
            pass
        return val == favorable_outcome

    binary_target = target_series.apply(matches_favorable)
    favorable_count = int(binary_target.sum())
    unfavorable_count = int((~binary_target & target_series.notna()).sum())
    missing_target_count = int(target_series.isna().sum())
    overall_favorable_rate = float(round(favorable_count / (total_rows - missing_target_count), 4)) if (total_rows - missing_target_count) > 0 else 0.0

    target_profile = {
        "column_name": target_col,
        "favorable_outcome": str(favorable_outcome),
        "total_records": total_rows,
        "favorable_count": favorable_count,
        "unfavorable_count": unfavorable_count,
        "missing_count": missing_target_count,
        "overall_favorable_rate": overall_favorable_rate,
        "favorable_percentage": round(overall_favorable_rate * 100, 2),
    }

    sensitive_profiles: Dict[str, Any] = {}
    data_quality_warnings: List[str] = []

    if missing_target_count > 0:
        data_quality_warnings.append(
            f"Target variable '{target_col}' has {missing_target_count} missing values ({round((missing_target_count/total_rows)*100, 2)}%)."
        )

    for col in sensitive_cols:
        group_series = df[col]
        col_null_count = int(group_series.isna().sum())
        if col_null_count > 0:
            data_quality_warnings.append(
                f"Sensitive attribute '{col}' has {col_null_count} missing values ({round((col_null_count/total_rows)*100, 2)}%)."
            )

        groups_info: List[Dict[str, Any]] = []
        valid_mask = group_series.notna() & target_series.notna()
        sub_groups = group_series[valid_mask].unique()

        for group in sub_groups:
            group_mask = (group_series == group) & target_series.notna()
            group_size = int(group_mask.sum())
            group_favorable = int((group_mask & binary_target).sum())
            fav_rate = float(round(group_favorable / group_size, 4)) if group_size > 0 else 0.0
            representation_pct = float(round((group_size / total_rows) * 100, 2))

            if group_size < 30:
                data_quality_warnings.append(
                    f"Subgroup '{group}' in attribute '{col}' has a small sample size (N={group_size} < 30). Statistical tests for this group may have low power."
                )

            groups_info.append({
                "group_name": str(group),
                "count": group_size,
                "representation_percentage": representation_pct,
                "favorable_count": group_favorable,
                "favorable_rate": fav_rate,
                "favorable_percentage": round(fav_rate * 100, 2),
            })

        # Sort by group name or count
        groups_info.sort(key=lambda x: x["count"], reverse=True)

        sensitive_profiles[col] = {
            "attribute_name": col,
            "missing_count": col_null_count,
            "unique_groups_count": len(sub_groups),
            "groups": groups_info,
        }

    return {
        "target_profile": target_profile,
        "sensitive_profiles": sensitive_profiles,
        "data_quality_warnings": list(dict.fromkeys(data_quality_warnings)),
    }
