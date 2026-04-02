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
        if not content or not content.strip():
            continue
        lines.extend([f"## {title}", content, ""])

    lines.extend([
        "## Scorecard",
        f"- **Overall score:** {bundle.scorecard.overall_score:.1f}/100",
        f"- **Recommendation:** {bundle.scorecard.recommendation}",
        f"- **Weighted dimension score:** {bundle.scorecard.weighted_dimension_score:.1f}/100",
        f"- **Confidence index:** {bundle.scorecard.confidence_index:.1f}/100",
        f"- **Coverage index:** {bundle.scorecard.coverage_index:.1f}/100",
        f"- **Conflict index:** {bundle.scorecard.conflict_index:.1f}/100",
        f"- **Gap penalty:** {bundle.scorecard.gap_penalty:.1f}",
        "",
        "| Dimension | Score | Weight | Evidence | Confidence | Coverage | Conflict |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for dimension in bundle.scorecard.dimensions:
        lines.append(
            f"| {dimension.dimension} | {dimension.score}/5 | {dimension.weight}% "
            f"| {dimension.evidence_count} | {dimension.average_confidence:.2f} "
            f"| {dimension.coverage_ratio:.0%} | {dimension.conflict_ratio:.0%} |"
        )

    lines.extend(["", "## Top Signals"])
    lines.extend(f"- {item}" for item in bundle.top_signals or ["No top signals recorded."])
    lines.extend(["", "## Top Risks"])
    lines.extend(f"- {item}" for item in bundle.top_risks or ["No top risks recorded."])
    lines.extend(["", "## Open Questions"])
    lines.extend(
        f"- {item}" for item in bundle.open_questions or ["No open questions recorded."]
    )

    if bundle.evidence_gaps:
        lines.extend(["", "## Evidence Gaps"])
        lines.extend(f"- {item}" for item in bundle.evidence_gaps)

    lines.extend(["", "## Citations"])
    lines.extend(f"- {item}" for item in bundle.citations or ["No citations recorded."])
    return "\n".join(lines) + "\n"
