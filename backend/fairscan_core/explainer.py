import os
from typing import Dict, Any, Optional
import json


def generate_audit_explanation(
    audit_results: Dict[str, Any],
    findings: Dict[str, Any],
    llm_provider: str = "auto",  # auto, groq, gemini, deterministic
    groq_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Translates statistical results into everyday, plain English so anyone can understand.
    Strictly forbids academic or mathematical jargon (e.g. SPD, Wilson intervals, DIR).
    """
    groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
    gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    summary_payload = {
        "target_col": audit_results.get("target_col"),
        "favorable_outcome": audit_results.get("favorable_outcome"),
        "total_records": audit_results.get("total_records"),
        "adverse_impact_count": findings.get("adverse_impact_count", 0),
        "attribute_summaries": {},
    }

    for col, data in audit_results.get("attribute_audits", {}).items():
        if data.get("status") == "completed":
            summary_payload["attribute_summaries"][col] = {
                "benchmark_group": data.get("reference_group"),
                "groups": {
                    g: {
                        "people_count": s["total_count"],
                        "success_rate_percent": s["selection_rate_pct"],
                        "comparison_ratio_to_benchmark": data["disparate_impact"]["comparisons"].get(g, {}).get("ratio"),
                    }
                    for g, s in data.get("group_stats", {}).items()
                }
            }

    prompt = (
        "You are explaining the results of a fairness test on a dataset to a non-technical person who has no math or data science background. "
        "Explain what was found using simple, friendly, everyday English.\n\n"
        f"DATA SUMMARY:\n{json.dumps(summary_payload, indent=2)}\n\n"
        "STRICT WRITING RULES:\n"
        "1. DO NOT USE complex technical or statistical jargon like 'Disparate Impact', 'Statistical Parity Difference', 'DIR', 'SPD', 'four-fifths', 'stochastic', 'Wilson interval', or 'p-value'.\n"
        "2. Instead use simple terms like 'success rate', 'fairness gap', 'positive decisions', 'comparison group', and 'bias warning'.\n"
        "3. Section 1: Quick Summary (2-3 sentences explaining in simple words if the dataset has an unfair bias or if it looks balanced).\n"
        "4. Section 2: What the numbers mean (give the real percentage success rates for each group and explain who got treated better or worse).\n"
        "5. Section 3: What could happen if you use this data (explain in plain words what would happen if an AI trains on this data).\n"
        "6. Section 4: 3 simple things to do next.\n"
        "7. Keep it concise, direct, and very easy to read."
    )

    # 1. Try Groq
    if (llm_provider in ["auto", "groq"]) and groq_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_key)
            completion = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": "You explain data bias and fairness in simple, easy-to-understand everyday English without academic jargon."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=900,
            )
            text = completion.choices[0].message.content
            if text and len(text.strip()) > 50:
                return {
                    "source": "Groq AI (Plain-English Summary)",
                    "explanation_text": text,
                    "privacy_safe": True,
                    "provider": "groq",
                }
        except Exception:
            pass

    # 2. Try Gemini
    if (llm_provider in ["auto", "gemini"]) and gemini_key:
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 900}
            }
            resp = requests.post(url, headers=headers, json=body, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                llm_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "source": "Google Gemini (Plain-English Summary)",
                    "explanation_text": llm_text,
                    "privacy_safe": True,
                    "provider": "gemini",
                }
        except Exception:
            pass

    # 3. Simple, Non-Jargon Deterministic Engine
    target_name = audit_results.get("target_col", "Outcome")
    fav_val = audit_results.get("favorable_outcome", "Positive")
    adv_count = findings.get("adverse_impact_count", 0)

    lines = []
    lines.append(f"### The Quick Take\n")
    if adv_count > 0:
        lines.append(
            f"⚠️ **Bias Warning:** The data shows a clear disadvantage for **{adv_count} group(s)** when it comes to getting a positive result (`{fav_val}`) for `{target_name}`. "
            f"If an AI or automated system trains on this dataset without fixing this first, it will learn these unfair past patterns and repeat them on new people."
        )
    else:
        lines.append(
            f"✅ **Looking Good:** All demographic groups receive positive outcomes (`{fav_val}`) at reasonably fair and balanced rates. "
            f"There are no major red flags jumping out in this dataset."
        )

    lines.append(f"\n### What the Numbers Show\n")
    for attr, details in summary_payload.get("attribute_summaries", {}).items():
        ref = details.get("benchmark_group")
        lines.append(f"Looking at **{attr}**:")
        for g_name, g_info in details.get("groups", {}).items():
            rate = g_info['success_rate_percent']
            count = g_info['people_count']
            ratio = g_info['comparison_ratio_to_benchmark']
            if g_name == ref:
                lines.append(f"• **{g_name}** (Benchmark Group): **{rate}%** received a positive result (Total: {count} people).")
            else:
                ratio_str = f"gets positive results at {round(ratio * 100, 1)}% the rate of the benchmark group" if ratio is not None else "has no calculable ratio"
                warning = " 🚨 (Below the standard 80% fairness threshold)" if ratio is not None and ratio < 0.8 else ""
                lines.append(f"• **{g_name}**: **{rate}%** received a positive result ({count} people). This group {ratio_str}.{warning}")

    lines.append(f"\n### What You Should Do Next\n")
    for idx, step in enumerate(findings.get("investigation_recommendations", []), 1):
        lines.append(f"{idx}. {step}")

    return {
        "source": "Plain-English Guide",
        "explanation_text": "\n".join(lines),
        "privacy_safe": True,
        "provider": "deterministic",
    }
