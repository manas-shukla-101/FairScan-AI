import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


class FairnessCalculationError(Exception):
    """Custom exception raised when fairness metric cannot be computed."""
    pass


def compute_group_selection_rates(
    df: pd.DataFrame,
    target_col: str,
    favorable_outcome: Any,
    sensitive_col: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute group-level selection rates, positive counts, and denominators.
    Guarantees no modification of original DataFrame.
    """
    valid_df = df[[target_col, sensitive_col]].dropna()
    if valid_df.empty:
        raise FairnessCalculationError(f"No valid non-null rows found for columns '{target_col}' and '{sensitive_col}'.")

    def is_fav(val):
        if str(val).strip().lower() == str(favorable_outcome).strip().lower():
            return 1
        try:
            if float(val) == float(favorable_outcome):
                return 1
        except (ValueError, TypeError):
            pass
        return 1 if val == favorable_outcome else 0

    valid_df = valid_df.copy()
    valid_df["is_favorable"] = valid_df[target_col].apply(is_fav)

    results: Dict[str, Dict[str, Any]] = {}
    grouped = valid_df.groupby(sensitive_col)

    for group_val, grp in grouped:
        group_key = str(group_val)
        n = len(grp)
        fav_n = int(grp["is_favorable"].sum())
        rate = fav_n / n if n > 0 else 0.0

        # Wilson score interval for binomial proportion confidence interval (95%)
        z = 1.96
        p = rate
        if n > 0:
            denom = 1 + z**2 / n
            center = (p + z**2 / (2 * n)) / denom
            spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
            ci_lower = max(0.0, center - spread)
            ci_upper = min(1.0, center + spread)
        else:
            ci_lower, ci_upper = 0.0, 0.0

        results[group_key] = {
            "group": group_key,
            "total_count": n,
            "favorable_count": fav_n,
            "unfavorable_count": n - fav_n,
            "selection_rate": round(rate, 4),
            "selection_rate_pct": round(rate * 100, 2),
            "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
        }

    return results


def calculate_statistical_parity(
    group_stats: Dict[str, Dict[str, Any]],
    reference_group: str,
) -> Dict[str, Any]:
    """
    Statistical Parity Difference (SPD) = Rate(Unprivileged) - Rate(Privileged/Reference)
    Ideal value: 0.0.
    Parity range: typically [-0.1, +0.1].
    """
    if reference_group not in group_stats:
        raise FairnessCalculationError(
            f"Reference group '{reference_group}' is not present in group statistics. Available: {list(group_stats.keys())}"
        )

    ref_rate = group_stats[reference_group]["selection_rate"]
    ref_n = group_stats[reference_group]["total_count"]
    ref_fav = group_stats[reference_group]["favorable_count"]

    comparisons: Dict[str, Any] = {}
    max_disparity = 0.0

    for group_key, stats_data in group_stats.items():
        if group_key == reference_group:
            comparisons[group_key] = {
                "difference": 0.0,
                "is_reference": True,
                "p_value": 1.0,
                "statistically_significant": False,
                "interpretation": "Reference Group (Benchmark)",
            }
            continue

        comp_rate = stats_data["selection_rate"]
        comp_n = stats_data["total_count"]
        comp_fav = stats_data["favorable_count"]

        spd = comp_rate - ref_rate
        if abs(spd) > abs(max_disparity):
            max_disparity = spd

        # Chi-square or Fisher's Exact test for difference in proportions
        contingency_table = [
            [comp_fav, comp_n - comp_fav],
            [ref_fav, ref_n - ref_fav]
        ]
        try:
            # If any expected cell count is small, use Fisher exact test if 2x2
            if comp_n < 30 or ref_n < 30:
                _, p_val = stats.fisher_exact(contingency_table)
            else:
                chi2, p_val, _, _ = stats.chi2_contingency(contingency_table, correction=True)
        except Exception:
            p_val = 1.0

        p_val_rounded = round(float(p_val), 5)
        is_sig = bool(p_val < 0.05)

        if abs(spd) <= 0.10:
            interp = "Fair (Success rate is within 10% of the comparison group)"
            status = "pass"
        elif spd < -0.10:
            interp = f"Disadvantage ({round(abs(spd)*100, 1)}% lower success rate than comparison group)"
            status = "warning" if spd >= -0.20 else "fail"
        else:
            interp = f"Advantage ({round(spd*100, 1)}% higher success rate than comparison group)"
            status = "info"

        comparisons[group_key] = {
            "difference": round(spd, 4),
            "difference_pct": round(spd * 100, 2),
            "is_reference": False,
            "p_value": p_val_rounded,
            "statistically_significant": is_sig,
            "interpretation": interp,
            "status": status,
        }

    return {
        "metric_name": "Success Rate Gap",
        "technical_name": "Statistical Parity Difference",
        "definition": "The difference in success rates between each group and the top comparison group.",
        "ideal_value": 0.0,
        "reference_group": reference_group,
        "max_absolute_difference": round(abs(max_disparity), 4),
        "comparisons": comparisons,
        "limitations": "Shows the direct difference in percentages without checking if groups differed in background qualifications.",
    }


def calculate_disparate_impact(
    group_stats: Dict[str, Dict[str, Any]],
    reference_group: str,
) -> Dict[str, Any]:
    """
    Disparate Impact Ratio (DIR) = Rate(Unprivileged) / Rate(Privileged/Reference)
    Threshold: EEOC Four-Fifths (80%) Rule -> DIR >= 0.80 and <= 1.25.
    Explicitly handles zero denominators.
    """
    if reference_group not in group_stats:
        raise FairnessCalculationError(f"Reference group '{reference_group}' not found.")

    ref_rate = group_stats[reference_group]["selection_rate"]

    comparisons: Dict[str, Any] = {}
    violations_count = 0

    for group_key, stats_data in group_stats.items():
        if group_key == reference_group:
            comparisons[group_key] = {
                "ratio": 1.0,
                "is_reference": True,
                "violates_80_rule": False,
                "zero_denominator": False,
                "interpretation": "Top Comparison Group (Standard = 100%)",
                "status": "pass",
            }
            continue

        comp_rate = stats_data["selection_rate"]

        # Handle zero denominators or zero numerator
        if ref_rate == 0.0 and comp_rate == 0.0:
            ratio = 1.0
            zero_denom = False
            interp = "Both groups have 0% success rate."
            violates = False
            status = "pass"
        elif ref_rate == 0.0:
            ratio = None
            zero_denom = True
            interp = "Undefined (The comparison group has a 0% success rate)."
            violates = False
            status = "inapplicable"
        else:
            ratio = round(comp_rate / ref_rate, 4)
            zero_denom = False
            violates = bool(ratio < 0.80)
            if violates:
                violations_count += 1
                status = "fail" if ratio < 0.60 else "warning"
                interp = f"Unfair Gap: This group receives positive results at only {round(ratio * 100, 1)}% the rate of the top group (below standard 80% fairness threshold)."
            elif ratio > 1.25:
                status = "info"
                interp = f"Above Standard: This group receives positive results at {round(ratio * 100, 1)}% the rate of the comparison group."
            else:
                status = "pass"
                interp = f"Fair: This group receives positive results at {round(ratio * 100, 1)}% the rate of the comparison group (passes the 80% rule)."

        comparisons[group_key] = {
            "ratio": ratio,
            "is_reference": False,
            "violates_80_rule": violates,
            "zero_denominator": zero_denom,
            "interpretation": interp,
            "status": status,
        }

    return {
        "metric_name": "Fairness Ratio",
        "technical_name": "Disparate Impact Ratio",
        "definition": "How a group's success rate compares to the top group as a percentage. Standard rules say this should be at least 80%.",
        "ideal_value": 1.0,
        "eeoc_threshold": 0.80,
        "reference_group": reference_group,
        "adverse_impact_violations": violations_count,
        "comparisons": comparisons,
        "limitations": "Small group sizes can cause percentages to swing wildly by chance.",
    }


def calculate_model_fairness_metrics(
    df: pd.DataFrame,
    target_col: str,
    prediction_col: Optional[str],
    favorable_outcome: Any,
    sensitive_col: str,
    reference_group: str,
) -> Dict[str, Any]:
    """
    Computes Equalized Odds and Equal Opportunity when model prediction column is supplied.
    Strictly forbids computing these without explicit model predictions.
    """
    if not prediction_col or prediction_col not in df.columns:
        return {
            "status": "unavailable",
            "reason": "Model-level metrics (Equalized Odds, Equal Opportunity) require a separate model prediction column in addition to ground-truth labels.",
            "metrics": {},
        }

    valid_df = df[[target_col, prediction_col, sensitive_col]].dropna()
    if valid_df.empty:
        return {
            "status": "unavailable",
            "reason": "No complete non-null rows matching ground truth, predictions, and sensitive attribute.",
            "metrics": {},
        }

    def is_fav(val):
        if str(val).strip().lower() == str(favorable_outcome).strip().lower():
            return 1
        try:
            if float(val) == float(favorable_outcome):
                return 1
        except (ValueError, TypeError):
            pass
        return 1 if val == favorable_outcome else 0

    valid_df = valid_df.copy()
    valid_df["y_true"] = valid_df[target_col].apply(is_fav)
    valid_df["y_pred"] = valid_df[prediction_col].apply(is_fav)

    groups = valid_df[sensitive_col].unique()
    group_rates = {}

    for g in groups:
        grp = valid_df[valid_df[sensitive_col] == g]
        # True Positives, False Positives, Positives (True = 1), Negatives (True = 0)
        pos = grp[grp["y_true"] == 1]
        neg = grp[grp["y_true"] == 0]

        tpr = float(pos["y_pred"].sum() / len(pos)) if len(pos) > 0 else 0.0
        fpr = float(neg["y_pred"].sum() / len(neg)) if len(neg) > 0 else 0.0

        group_rates[str(g)] = {
            "tpr": round(tpr, 4),  # True Positive Rate (Recall / Opportunity)
            "fpr": round(fpr, 4),  # False Positive Rate
            "count": len(grp),
            "positives": len(pos),
            "negatives": len(neg),
        }

    if reference_group not in group_rates:
        return {
            "status": "error",
            "reason": f"Reference group '{reference_group}' not found in prediction dataset.",
            "metrics": {},
        }

    ref_tpr = group_rates[reference_group]["tpr"]
    ref_fpr = group_rates[reference_group]["fpr"]

    equal_opportunity_diffs = {}
    equalized_odds_diffs = {}

    for g_key, r in group_rates.items():
        tpr_diff = round(r["tpr"] - ref_tpr, 4)
        fpr_diff = round(r["fpr"] - ref_fpr, 4)
        equal_opportunity_diffs[g_key] = tpr_diff
        equalized_odds_diffs[g_key] = {
            "tpr_diff": tpr_diff,
            "fpr_diff": fpr_diff,
            "max_abs_diff": max(abs(tpr_diff), abs(fpr_diff)),
        }

    return {
        "status": "available",
        "reference_group": reference_group,
        "group_rates": group_rates,
        "equal_opportunity": {
            "metric_name": "Equal Opportunity Difference",
            "definition": "Difference in True Positive Rate (TPR) between groups (TPR(Group) - TPR(Reference)).",
            "ideal_value": 0.0,
            "differences": equal_opportunity_diffs,
        },
        "equalized_odds": {
            "metric_name": "Equalized Odds Difference",
            "definition": "Requires both TPR and FPR to be equal across groups compared to reference group.",
            "ideal_value": 0.0,
            "differences": equalized_odds_diffs,
        },
    }


def run_full_dataset_audit(
    df: pd.DataFrame,
    target_col: str,
    favorable_outcome: Any,
    sensitive_cols: List[str],
    reference_groups: Dict[str, str],
    prediction_col: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a comprehensive fairness audit across all configured sensitive attributes.
    Returns complete metric breakdowns, statistical checks, and warnings.
    """
    if len(df) == 0:
        raise FairnessCalculationError("Cannot audit an empty dataset.")

    audit_results: Dict[str, Any] = {
        "target_col": target_col,
        "favorable_outcome": str(favorable_outcome),
        "total_records": len(df),
        "attribute_audits": {},
    }

    for col in sensitive_cols:
        # Check single group dataset
        uniques = df[col].dropna().unique()
        if len(uniques) < 2:
            audit_results["attribute_audits"][col] = {
                "status": "inapplicable",
                "reason": f"Attribute '{col}' only contains 1 unique value ({list(uniques)}). Disparity comparisons require at least 2 distinct groups.",
                "group_stats": {},
            }
            continue

        ref_group = reference_groups.get(col)
        if not ref_group or ref_group not in [str(u) for u in uniques]:
            # Default to largest group as reference if not specified
            val_counts = df[col].value_counts()
            ref_group = str(val_counts.index[0])

        group_stats = compute_group_selection_rates(
            df=df,
            target_col=target_col,
            favorable_outcome=favorable_outcome,
            sensitive_col=col,
        )

        stat_parity = calculate_statistical_parity(
            group_stats=group_stats,
            reference_group=ref_group,
        )

        disp_impact = calculate_disparate_impact(
            group_stats=group_stats,
            reference_group=ref_group,
        )

        model_metrics = calculate_model_fairness_metrics(
            df=df,
            target_col=target_col,
            prediction_col=prediction_col,
            favorable_outcome=favorable_outcome,
            sensitive_col=col,
            reference_group=ref_group,
        )

        audit_results["attribute_audits"][col] = {
            "status": "completed",
            "attribute_name": col,
            "reference_group": ref_group,
            "group_stats": group_stats,
            "statistical_parity": stat_parity,
            "disparate_impact": disp_impact,
            "model_fairness": model_metrics,
        }

    return audit_results
