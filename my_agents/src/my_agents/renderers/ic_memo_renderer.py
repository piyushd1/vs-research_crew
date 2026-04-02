from __future__ import annotations

from my_agents.schemas import FindingsBundle


def render_ic_memo(bundle: FindingsBundle) -> str:
    lines = [
        f"# IC Memo: {bundle.company_name}",
        "",
        "## Executive Summary",
        bundle.sections.get("executive_summary", bundle.summary),
        "",
    ]

    # Company snapshot (key metrics table)
    snapshot = bundle.sections.get("company_snapshot")
    if snapshot:
        lines.extend(["## Company Snapshot", snapshot, ""])

    lines.extend([
        "## Investment Recommendation",
        bundle.sections.get("investment_recommendation", "Recommendation unavailable."),
        "",
        "## Scorecard",
        f"- **Overall score:** {bundle.scorecard.overall_score:.1f}/100",
        f"- **Recommendation:** {bundle.scorecard.recommendation}",
        f"- **Weighted dimension score:** {bundle.scorecard.weighted_dimension_score:.1f}/100",
        f"- **Confidence index:** {bundle.scorecard.confidence_index:.1f}/100",
        f"- **Coverage index:** {bundle.scorecard.coverage_index:.1f}/100",
        f"- **Conflict index:** {bundle.scorecard.conflict_index:.1f}/100",
        f"- **Gap penalty:** {bundle.scorecard.gap_penalty:.1f}",
        "",
        "| Dimension | Score | Weight |",
        "| --- | --- | --- |",
    ])
    for dimension in bundle.scorecard.dimensions:
        lines.append(
            f"| {dimension.dimension} | {dimension.score}/5 | {dimension.weight}% |"
        )

    # Workflow-specific dynamic sections
    optional_sections = {
        "market_landscape": "Market Landscape",
        "financial_analysis": "Financial Analysis",
        "product_technology": "Product & Technology",
        "founder_assessment": "Founder Assessment",
        "gtm_momentum": "GTM Momentum",
        "regulatory_compliance": "Regulatory & Compliance",
        "risk_register": "Risk Register",
        "portfolio_health": "Portfolio Health",
        "support_recommendations": "Support Recommendations",
    }
    for key, title in optional_sections.items():
        content = bundle.sections.get(key)
        if content and content.strip():
            lines.extend(["", f"## {title}", content])

    lines.extend(["", "## Top Signals"])
    lines.extend(f"- {item}" for item in bundle.top_signals or ["No top signals recorded."])
    lines.extend(["", "## Top Risks"])
    lines.extend(f"- {item}" for item in bundle.top_risks or ["No top risks recorded."])
    lines.extend(["", "## Open Questions"])
    lines.extend(
        f"- {item}" for item in bundle.open_questions or ["No open questions recorded."]
    )

    # Evidence gaps
    if bundle.evidence_gaps:
        lines.extend(["", "## Evidence Gaps"])
        lines.extend(f"- {item}" for item in bundle.evidence_gaps)

    lines.extend(["", "## Citations"])
    lines.extend(f"- {item}" for item in bundle.citations or ["No citations recorded."])
    return "\n".join(lines) + "\n"
