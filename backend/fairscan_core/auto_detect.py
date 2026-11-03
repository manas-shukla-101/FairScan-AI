from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


# Common target/decision column patterns
TARGET_KEYWORDS = [
    "target", "label", "outcome", "decision", "approved", "hired", "accepted",
    "admitted", "selected", "churn", "default", "promoted", "funded", "grant",
    "passed", "result", "class", "y", "status", "action"
]

# Common protected/sensitive attribute keywords
SENSITIVE_KEYWORDS = [
    "gender", "sex", "race", "ethnicity", "age", "age_group", "nationality",
    "religion", "disability", "marital", "marital_status", "veteran", "citizenship",
    "language", "caste", "tribe", "sexual_orientation"
]

# Values that typically signify favorable outcomes
FAVORABLE_CANDIDATE_STRINGS = [
    "1", "true", "yes", "approved", "hired", "accepted", "admitted",
    "selected", "promoted", "pass", "passed", "grant", "granted", "funded", "good"
]


def auto_detect_audit_configuration(
    df: pd.DataFrame,
    columns_info: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Intelligently auto-discovers:
    1. The primary target / decision variable.
    2. The most favorable outcome value.
    3. All sensitive / protected attributes.
    4. The benchmark reference group for each sensitive attribute.
    5. Any candidate model prediction column.
    """
    col_names = list(df.columns)
    col_name_lower_map = {c: c.strip().lower() for c in col_names}

    # 1. Detect Target Column
    target_candidate = None
    target_score = -1

    for c in columns_info:
        name = c["name"]
        name_lower = col_name_lower_map[name]
        unique_cnt = c["unique_count"]

        # Disqualify if only 1 unique value or too many unique values (e.g. ID or continuous)
        if unique_cnt < 2 or unique_cnt > 20:
            continue

        score = 0
        # If binary, strong candidate
        if unique_cnt == 2:
            score += 40
        elif unique_cnt <= 5:
            score += 15

        # Check for target keywords
        for kw in TARGET_KEYWORDS:
            if kw in name_lower:
                score += 50
                break

        # If it has prediction in name, penalize as it might be model prediction
        if "pred" in name_lower or "prob" in name_lower:
            score -= 30

        if score > target_score:
            target_score = score
            target_candidate = name

    # Fallback if no target matched keywords: pick the first binary column, or first categorical
    if not target_candidate:
        binary_cols = [c["name"] for c in columns_info if c["is_binary"]]
        if binary_cols:
            target_candidate = binary_cols[-1]  # Targets are often at the end
        elif col_names:
            target_candidate = col_names[-1]

    # 2. Detect Favourable Outcome for target
    favorable_candidate = None
    if target_candidate and target_candidate in df.columns:
        target_series = df[target_candidate].dropna()
        uniques = [
            val.item() if hasattr(val, "item") else val
            for val in target_series.unique()
        ]

        # Check against known favorable values
        for val in uniques:
            s_val = str(val).strip().lower()
            if s_val in FAVORABLE_CANDIDATE_STRINGS:
                favorable_candidate = val
                break

        # Fallback for binary {0, 1}
        if favorable_candidate is None and set(uniques).issubset({0, 1, "0", "1"}):
            favorable_candidate = 1 if (1 in uniques) else "1"

        # Fallback: pick the first value if still none
        if favorable_candidate is None and uniques:
            favorable_candidate = uniques[0]

    # 3. Detect Sensitive / Protected Attributes
    sensitive_candidates = []
    reference_groups = {}

    for c in columns_info:
        name = c["name"]
        name_lower = col_name_lower_map[name]
        unique_cnt = c["unique_count"]

        # Must not be the target column
        if name == target_candidate:
            continue

        # Sensitive attributes are categorical (usually 2 to 15 unique groups)
        if unique_cnt < 2 or unique_cnt > 15:
            continue

        is_sensitive = False
        for kw in SENSITIVE_KEYWORDS:
            if kw in name_lower:
                is_sensitive = True
                break

        if is_sensitive:
            sensitive_candidates.append(name)
            # Reference group: default to the largest group (standard benchmark practice)
            val_counts = df[name].dropna().value_counts()
            if not val_counts.empty:
                reference_groups[name] = str(val_counts.index[0])

    # If no demographic keywords matched, automatically include up to 2 low-cardinality categorical columns
    if not sensitive_candidates:
        categorical_cols = [
            c["name"] for c in columns_info
            if c["name"] != target_candidate and 2 <= c["unique_count"] <= 8
        ]
        sensitive_candidates = categorical_cols[:2]
        for col in sensitive_candidates:
            val_counts = df[col].dropna().value_counts()
            if not val_counts.empty:
                reference_groups[col] = str(val_counts.index[0])

    # 4. Detect Model Prediction Column (if any)
    prediction_candidate = None
    for c in columns_info:
        name = c["name"]
        name_lower = col_name_lower_map[name]
        if name == target_candidate or name in sensitive_candidates:
            continue
        if "pred" in name_lower or "score" in name_lower or "model" in name_lower:
            prediction_candidate = name
            break

    return {
        "auto_target_col": target_candidate,
        "auto_favorable_outcome": str(favorable_candidate) if favorable_candidate is not None else None,
        "auto_sensitive_cols": sensitive_candidates,
        "auto_reference_groups": reference_groups,
        "auto_prediction_col": prediction_candidate,
        "has_detected_configuration": bool(target_candidate and sensitive_candidates),
    }

