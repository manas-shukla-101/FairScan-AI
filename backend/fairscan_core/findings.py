from typing import Dict, Any, List


def generate_deterministic_findings(
    audit_results: Dict[str, Any],
    profile_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generates plain-English findings, warnings, and next steps in simple, human language.
    No statistics jargon: explains what was found and what it means clearly.
    """
    findings_list: List[Dict[str, Any]] = []
    investigations: List[str] = []
    adverse_impact_count = 0
    severe_disparity_count = 0

    attr_audits = audit_results.get("attribute_audits", {})

    for col, audit in attr_audits.items():
        if audit.get("status") == "inapplicable":
            findings_list.append({
                "type": "warning",
                "attribute": col,
                "title": f"Only One Group Found in '{col}'",
                "summary": f"All rows in '{col}' belong to the same category. Comparing fairness requires at least two different groups.",
                "detail": "To check for fairness, your dataset needs people from multiple groups (for example, both men and women).",
            })
            continue

        ref_group = audit.get("reference_group")
        group_stats = audit.get("group_stats", {})
        stat_parity = audit.get("statistical_parity", {})
        disp_impact = audit.get("disparate_impact", {})

        for grp_key, grp_data in group_stats.items():
            if grp_key == ref_group:
                continue

            n = grp_data["total_count"]
            fav_n = grp_data["favorable_count"]
            rate_pct = grp_data["selection_rate_pct"]

            ref_data = group_stats.get(ref_group, {})
            ref_n = ref_data.get("total_count", 0)
            ref_rate_pct = ref_data.get("selection_rate_pct", 0)

            di_comp = disp_impact.get("comparisons", {}).get(grp_key, {})
            di_ratio = di_comp.get("ratio")
            sp_comp = stat_parity.get("comparisons", {}).get(grp_key, {})
            spd = sp_comp.get("difference", 0.0)
            p_val = sp_comp.get("p_value", 1.0)
            is_sig = sp_comp.get("statistically_significant", False)

            if di_comp.get("zero_denominator"):
                findings_list.append({
                    "type": "info",
                    "attribute": col,
                    "title": f"No Positive Results for '{ref_group}'",
                    "summary": f"Nobody in the '{ref_group}' benchmark group received a positive outcome (0 out of {ref_n}). Because of this, a percentage ratio cannot be calculated.",
                    "detail": "Look at the direct success rate for each group instead of the ratio.",
                })
                continue

            if di_comp.get("violates_80_rule"):
                adverse_impact_count += 1
                sig_text = " This gap is large enough to be unlikely to happen by pure chance." if is_sig else " This might be due to a small sample size."
                ratio_pct = round(di_ratio * 100, 1) if di_ratio is not None else 0
                gap_pct = round(abs(rate_pct - ref_rate_pct), 1)

                findings_list.append({
                    "type": "critical",
                    "attribute": col,
                    "title": f"Unfair Advantage Detected: '{grp_key}' vs '{ref_group}'",
                    "summary": (
                        f"People in '{grp_key}' got a positive result only {rate_pct}% of the time ({fav_n} out of {n}), "
                        f"while '{ref_group}' got it {ref_rate_pct}% of the time ({ref_data.get('favorable_count', 0)} out of {ref_n}). "
                        f"That is a {gap_pct}% gap. The success rate for '{grp_key}' is only {ratio_pct}% of '{ref_group}' "
                        f"(standard fairness rules say it should be at least 80%).{sig_text}"
                    ),
                    "detail": "This is a big red flag for bias. If an AI is trained on this data, it will likely learn to give lower scores to this group.",
                })
            elif spd < -0.10:
                severe_disparity_count += 1
                gap_pct = round(abs(spd * 100), 1)
                findings_list.append({
                    "type": "warning",
                    "attribute": col,
                    "title": f"Notable Success Gap for '{grp_key}'",
                    "summary": f"'{grp_key}' has a {gap_pct}% lower success rate than '{ref_group}'.",
                    "detail": "Even though it narrowly meets the 80% rule, this difference is still worth reviewing before training a model.",
                })

            if n < 30:
                findings_list.append({
                    "type": "warning",
                    "attribute": col,
                    "title": f"Small Group Size Warning: '{grp_key}'",
                    "summary": f"Only {n} people belong to '{grp_key}'.",
                    "detail": "When a group has fewer than 30 people, numbers can swing wildly from just 1 or 2 decisions. Collect more data on this group if possible.",
                })

    # Clear, simple next steps
    if adverse_impact_count > 0 or severe_disparity_count > 0:
        investigations.append("Check past decision-making: Look into why past human decisions favored one group over another.")
        investigations.append("Watch out for hidden stand-in variables: Features like zip code, school attended, or club membership can act as secret proxies for gender or race.")
        investigations.append("Balance the data before training: Use the 'Fix Bias (Reweighting)' tab to give fair mathematical weights to underrepresented groups.")
        investigations.append("Verify qualification differences: Check if the gap is because of actual required qualifications (e.g. years of experience) rather than unfair bias.")
    else:
        investigations.append("Results look balanced: All groups receive positive outcomes at similar rates under standard 80% fairness guidelines.")
        investigations.append("Keep monitoring: Even if the overall numbers look fair, test your model predictions once it is trained.")

    investigations.append("Remember: Statistical numbers highlight where to look—they do not replace human judgment or legal advice.")

    return {
        "adverse_impact_count": adverse_impact_count,
        "total_findings": len(findings_list),
        "findings": findings_list,
        "investigation_recommendations": investigations,
        "disclaimer": (
            "FairScan is a helper tool to spot unfair patterns in data. It does not replace legal advice, "
            "and having equal numbers does not automatically guarantee full legal compliance."
        ),
    }
