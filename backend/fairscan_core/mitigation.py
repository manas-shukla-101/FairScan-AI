from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from .metrics import compute_group_selection_rates, calculate_statistical_parity, calculate_disparate_impact


def apply_dataset_reweighting(
    df: pd.DataFrame,
    target_col: str,
    favorable_outcome: Any,
    sensitive_col: str,
    reference_group: str,
) -> Dict[str, Any]:
    """
    Implements Kamiran & Calders sample reweighting.
    Preserves original dataset rows and computes per-sample weights so that:
      W(S=s, Y=y) = (P(S=s) * P(Y=y)) / P(S=s, Y=y)
    This neutralizes statistical parity differences without discarding data or altering ground labels.
    """
    valid_mask = df[target_col].notna() & df[sensitive_col].notna()
    work_df = df[valid_mask].copy()

    def is_fav(val):
        if str(val).strip().lower() == str(favorable_outcome).strip().lower():
            return 1
        try:
            if float(val) == float(favorable_outcome):
                return 1
        except (ValueError, TypeError):
            pass
        return 1 if val == favorable_outcome else 0

    work_df["y_binary"] = work_df[target_col].apply(is_fav)
    work_df["s_group"] = work_df[sensitive_col].astype(str)

    n_total = len(work_df)
    if n_total == 0:
        raise ValueError("Cannot reweight an empty dataset.")

    # Calculate marginal and joint probabilities
    # P(Y=y)
    p_y = work_df["y_binary"].value_counts(normalize=True).to_dict()
    # P(S=s)
    p_s = work_df["s_group"].value_counts(normalize=True).to_dict()
    # P(S=s, Y=y)
    p_sy = work_df.groupby(["s_group", "y_binary"]).size() / n_total

    weights = []
    weight_table = {}

    for idx, row in work_df.iterrows():
        s = row["s_group"]
        y = row["y_binary"]
        joint_p = p_sy.get((s, y), 0.0)
        expected_p = p_s.get(s, 0.0) * p_y.get(y, 0.0)
        
        w = float(expected_p / joint_p) if joint_p > 0 else 1.0
        weights.append(round(w, 4))
        
        key = f"{s} | Outcome={y}"
        if key not in weight_table:
            weight_table[key] = {
                "group": s,
                "outcome": "Positive Result (Accepted)" if y == 1 else "Negative Result (Rejected)",
                "sample_weight": round(w, 4),
                "joint_frequency": int(joint_p * n_total),
            }

    work_df["fairscan_sample_weight"] = weights

    # Compute baseline metrics (Before)
    before_stats = compute_group_selection_rates(work_df, target_col, favorable_outcome, "s_group")
    before_spd = calculate_statistical_parity(before_stats, reference_group)
    before_di = calculate_disparate_impact(before_stats, reference_group)

    # Compute weighted selection rates (After)
    after_stats = {}
    for grp_val, grp in work_df.groupby("s_group"):
        grp_k = str(grp_val)
        w_total = grp["fairscan_sample_weight"].sum()
        w_fav = grp[grp["y_binary"] == 1]["fairscan_sample_weight"].sum()
        w_rate = float(w_fav / w_total) if w_total > 0 else 0.0
        
        after_stats[grp_k] = {
            "group": grp_k,
            "total_count": len(grp),
            "effective_weighted_count": round(float(w_total), 2),
            "favorable_count": int(grp["y_binary"].sum()),
            "selection_rate": round(w_rate, 4),
            "selection_rate_pct": round(w_rate * 100, 2),
            "ci_95": [round(w_rate, 4), round(w_rate, 4)],
        }

    after_spd = calculate_statistical_parity(after_stats, reference_group)
    after_di = calculate_disparate_impact(after_stats, reference_group)

    # Format sample export with weights attached
    export_df = df.copy()
    export_df["sample_weight"] = 1.0
    export_df.loc[valid_mask, "sample_weight"] = weights

    csv_buffer = export_df.to_csv(index=False)

    return {
        "method": "Pre-processing Sample Reweighting (Kamiran & Calders)",
        "sensitive_col": sensitive_col,
        "reference_group": reference_group,
        "weight_multipliers": list(weight_table.values()),
        "before_metrics": {
            "group_stats": before_stats,
            "statistical_parity": before_spd,
            "disparate_impact": before_di,
        },
        "after_metrics": {
            "group_stats": after_stats,
            "statistical_parity": after_spd,
            "disparate_impact": after_di,
        },
        "tradeoff_notes": (
            "Reweighting achieves mathematical statistical parity across demographic subgroups during model training "
            "without corrupting ground labels. However, applying sample weights may slightly degrade standard overall accuracy "
            "if base group distributions differ due to legitimate predictive features."
        ),
        "reweighted_csv_preview": export_df.head(20).replace({np.nan: None}).to_dict(orient="records"),
        "total_rows_reweighted": len(work_df),
        "reweighted_csv_string": csv_buffer,
    }

