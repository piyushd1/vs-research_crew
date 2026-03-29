from __future__ import annotations

from my_agents.schemas import FindingsBundle


def render_ic_memo(bundle: FindingsBundle) -> str:
    lines = [
        f"# IC Memo: {bundle.company_name}",
        "",
        "## Executive Summary",
        bundle.sections.get("executive_summary", bundle.summary),
        "",
        "## Recommendation",
        bundle.sections.get("investment_recommendation", "Recommendation unavailable."),
        "",
        "## Scorecard",
        f"- Overall score: {bundle.scorecard.overall_score:.1f}/100",
        f"- Recommendation: {bundle.scorecard.recommendation}",
    ]
    for dimension in bundle.scorecard.dimensions:
        lines.append(
            f"- {dimension.dimension}: {dimension.score}/5 (weight {dimension.weight})"
        )

    # Workflow-specific dynamic sections
    optional_sections = {
        "market_landscape": "Market Landscape",
        "financial_analysis": "Financial Analysis",
        "product_technology": "Product & Technology",
        "founder_assessment": "Founder Assessment",
        "gtm_momentum": "GTM Momentum",
        "regulatory_compliance": "Regulatory & Compliance",
        "portfolio_health": "Portfolio Health",
        "support_recommendations": "Support Recommendations",
    }
    for key, title in optional_sections.items():
        if key in bundle.sections:
            lines.extend(["", f"## {title}", bundle.sections[key]])

    lines.extend(["", "## Top Signals"])
    lines.extend(
        f"- {item}" for item in bundle.top_signals or ["No top signals recorded."]
    )
    lines.extend(["", "## Top Risks"])
    lines.extend(f"- {item}" for item in bundle.top_risks or ["No top risks recorded."])
    lines.extend(["", "## Open Questions"])
    lines.extend(
        f"- {item}" for item in bundle.open_questions or ["No open questions recorded."]
    )
    return "\n".join(lines) + "\n"
