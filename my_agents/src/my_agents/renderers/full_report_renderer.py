from __future__ import annotations

from my_agents.schemas import FindingsBundle


SECTION_TITLES = {
    "executive_summary": "Executive Summary",
    "company_snapshot": "Company Snapshot",
    "market_landscape": "Market Landscape",
    "financial_analysis": "Financial Analysis",
    "product_technology": "Product & Technology",
    "founder_assessment": "Founder Assessment",
    "gtm_momentum": "GTM Momentum",
    "regulatory_compliance": "Regulatory & Compliance",
    "risk_register": "Risk Register",
    "investment_recommendation": "Investment Recommendation",
    "scorecard_summary": "Scorecard Summary",
    "open_questions": "Open Questions",
    "evidence_gaps": "Evidence Gaps",
    "portfolio_health": "Portfolio Health",
    "support_recommendations": "Support Recommendations",
    "next_steps": "Next Steps",
}


def render_full_report(bundle: FindingsBundle) -> str:
    lines = [f"# Full Report: {bundle.company_name}", ""]
    for key, title in SECTION_TITLES.items():
        content = bundle.sections.get(key)
        if not content:
            continue
        lines.extend([f"## {title}", content, ""])

    lines.extend(
        [
            "## Scorecard",
            f"- Overall score: {bundle.scorecard.overall_score:.1f}/100",
            f"- Recommendation: {bundle.scorecard.recommendation}",
            "",
        ]
    )
    lines.extend(
        f"- {dimension.dimension}: {dimension.score}/5 (weight {dimension.weight})"
        for dimension in bundle.scorecard.dimensions
    )
    lines.extend(["", "## Top Signals"])
    lines.extend(f"- {item}" for item in bundle.top_signals or ["No top signals recorded."])
    lines.extend(["", "## Top Risks"])
    lines.extend(f"- {item}" for item in bundle.top_risks or ["No top risks recorded."])
    lines.extend(["", "## Open Questions"])
    lines.extend(
        f"- {item}" for item in bundle.open_questions or ["No open questions recorded."]
    )
    lines.extend(["", "## Citations"])
    lines.extend(f"- {item}" for item in bundle.citations or ["No citations recorded."])
    return "\n".join(lines) + "\n"
