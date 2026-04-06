from __future__ import annotations

from my_agents.html_utils import markdownish_to_html_document
from my_agents.schemas import FindingsBundle, ReportStandardsAssessment, VCRubric


def render_standards_report(assessment: ReportStandardsAssessment) -> str:
    lines = [
        "# Report Standards Validation",
        "",
        f"## Profile",
        f"- Workflow: {assessment.workflow.value}",
        f"- Output profile: {assessment.output_profile.value}",
        f"- Benchmark: {assessment.industry_profile}",
        f"- Overall status: {assessment.overall_status.value}",
        "",
        "## Length",
        f"- Word count: {assessment.word_count}",
        f"- Target range: {assessment.target_word_range[0]}-{assessment.target_word_range[1]} words",
        f"- Length status: {assessment.length_status.value}",
        "",
        "## Structure",
        f"- Section coverage: {assessment.section_coverage:.0%}",
        f"- Required sections: {', '.join(assessment.required_sections) or 'None'}",
        f"- Present sections: {', '.join(assessment.present_sections) or 'None'}",
        f"- Missing sections: {', '.join(assessment.missing_sections) or 'None'}",
        "",
        "## Citations",
        f"- Citation count: {assessment.citation_count}",
        f"- Minimum expected citations: {assessment.minimum_citations}",
        f"- Citation density: {assessment.citation_density:.2f} citations per 1,000 words",
        "",
        "## Notes",
    ]
    lines.extend(f"- {note}" for note in assessment.notes or ["No validation notes."])
    return "\n".join(lines) + "\n"


def render_eval_report(
    bundle: FindingsBundle,
    rubric: VCRubric,
    assessment: ReportStandardsAssessment,
    eval_model: str,
    prompt_path: str | None = None,
) -> str:
    lines = [
        f"# Eval Report: {bundle.company_name}",
        "",
        "## Summary",
        rubric.summary_feedback,
        "",
        "## Judge Setup",
        f"- Eval model: {eval_model}",
        "- Method: LLM-as-a-judge plus deterministic format and standards checks",
        f"- Prompt path: {prompt_path or 'Not recorded'}",
        "",
        "## Composite Score",
        f"- Final eval score: {rubric.final_eval_score}/100",
        f"- Relevance: {rubric.relevance_score}/10",
        f"- Tone: {rubric.tone_score}/10",
        f"- Citation quality: {rubric.citation_quality_score}/10",
        f"- Structure: {rubric.structure_score}/10",
        f"- Length fit: {rubric.length_fit_score}/10",
        f"- Evidence strength: {rubric.evidence_strength_score}/10",
        f"- Actionability: {rubric.actionability_score}/10",
        "",
        "## Industry Validation",
        f"- Benchmark: {assessment.industry_profile}",
        f"- Standards status: {assessment.overall_status.value}",
        f"- Word count: {assessment.word_count}",
        f"- Target range: {assessment.target_word_range[0]}-{assessment.target_word_range[1]}",
        f"- Citation count: {assessment.citation_count}",
        f"- Missing required sections: {', '.join(assessment.missing_sections) or 'None'}",
        "",
    ]

    # Score divergence warning
    if bundle.scorecard:
        delta = abs(bundle.scorecard.overall_score - rubric.final_eval_score)
        if delta > 20:
            lines.extend([
                "## Score Divergence Warning",
                f"Scorecard ({bundle.scorecard.overall_score:.0f}/100) and eval "
                f"({rubric.final_eval_score}/100) diverge by {delta:.0f} points. "
                "This may indicate that report quality does not match the underlying "
                "evidence quality. Manual review recommended.",
                "",
            ])

    lines.append("## Hallucination Flags")
    lines.extend(
        f"- {item.finding_claim}: {item.rationale}"
        for item in rubric.hallucinations
        or []
    )
    if not rubric.hallucinations:
        lines.append("- None flagged.")
    lines.extend(["", "## Negative Constraint Violations"])
    lines.extend(
        f"- {item}" for item in rubric.negative_constraint_violations or ["None flagged."]
    )
    lines.extend(["", "## Improvement Actions"])
    lines.extend(f"- {item}" for item in rubric.improvement_actions or ["No actions suggested."])
    lines.extend(["", "## Validation Notes"])
    lines.extend(f"- {item}" for item in assessment.notes or ["No validation notes."])
    return "\n".join(lines) + "\n"


def render_eval_report_html(markdown_text: str, title: str) -> str:
    return markdownish_to_html_document(markdown_text, title)
