from __future__ import annotations

import re

from my_agents.schemas import (
    FindingsBundle,
    LengthStatus,
    OutputProfile,
    ReportStandardsAssessment,
    ValidationStatus,
    WorkflowType,
)


VISIBLE_TEXT_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"\b[\w/-]+\b")

WORD_RANGES: dict[OutputProfile, tuple[int, int]] = {
    OutputProfile.IC_MEMO: (3500, 6000),
    OutputProfile.FULL_REPORT: (4500, 8000),
    OutputProfile.ONE_PAGER: (400, 1000),
}

MIN_CITATIONS: dict[OutputProfile, int] = {
    OutputProfile.IC_MEMO: 5,
    OutputProfile.FULL_REPORT: 10,
    OutputProfile.ONE_PAGER: 4,
}

# Sections that live as list/object fields on FindingsBundle, not in sections dict
_LIST_FIELD_SECTIONS = {
    "top_signals": "top_signals",
    "top_risks": "top_risks",
    "open_questions": "open_questions",
    "evidence_gaps": "evidence_gaps",
}

INDUSTRY_PROFILE_LABELS: dict[tuple[WorkflowType, OutputProfile], str] = {
    (WorkflowType.SOURCING, OutputProfile.IC_MEMO): "VC sourcing memo",
    (WorkflowType.SOURCING, OutputProfile.FULL_REPORT): "VC sourcing diligence note",
    (WorkflowType.SOURCING, OutputProfile.ONE_PAGER): "VC sourcing partner one-pager",
    (WorkflowType.DUE_DILIGENCE, OutputProfile.IC_MEMO): "IC diligence memo",
    (WorkflowType.DUE_DILIGENCE, OutputProfile.FULL_REPORT): "Full diligence report",
    (WorkflowType.DUE_DILIGENCE, OutputProfile.ONE_PAGER): "Diligence summary one-pager",
    (WorkflowType.PORTFOLIO, OutputProfile.IC_MEMO): "Portfolio update memo",
    (WorkflowType.PORTFOLIO, OutputProfile.FULL_REPORT): "Portfolio review report",
    (WorkflowType.PORTFOLIO, OutputProfile.ONE_PAGER): "Portfolio board one-pager",
}


def _visible_text(rendered_output: str) -> str:
    if "<html" in rendered_output.lower():
        return VISIBLE_TEXT_RE.sub(" ", rendered_output)
    return rendered_output


def _is_section_present(key: str, bundle: FindingsBundle) -> bool:
    """Check whether a section key has content, checking list fields and scorecard too."""
    if key in _LIST_FIELD_SECTIONS:
        field_name = _LIST_FIELD_SECTIONS[key]
        field_value = getattr(bundle, field_name, None)
        return bool(field_value)
    if key == "scorecard_summary":
        return bool(bundle.scorecard and bundle.scorecard.dimensions)
    return bool(bundle.sections.get(key, "").strip())


def assess_report_standards(
    bundle: FindingsBundle,
    workflow: WorkflowType,
    output_profile: OutputProfile,
    rendered_output: str,
    required_sections: list[str],
) -> ReportStandardsAssessment:
    target_min, target_max = WORD_RANGES[output_profile]
    minimum_citations = MIN_CITATIONS[output_profile]
    visible_text = _visible_text(rendered_output)
    word_count = len(WORD_RE.findall(visible_text))
    citation_count = len(bundle.citations)
    present_sections = [
        key for key in required_sections if _is_section_present(key, bundle)
    ]
    missing_sections = [key for key in required_sections if key not in present_sections]
    section_coverage = len(present_sections) / max(len(required_sections), 1)
    citation_density = citation_count / max(word_count / 1000.0, 1.0)

    if word_count < target_min:
        length_status = LengthStatus.TOO_SHORT
    elif word_count > target_max:
        length_status = LengthStatus.TOO_LONG
    else:
        length_status = LengthStatus.TARGET

    notes: list[str] = []
    if length_status == LengthStatus.TOO_SHORT:
        notes.append(
            f"Output is short for a typical {output_profile.value} ({word_count} words vs target {target_min}-{target_max})."
        )
    if length_status == LengthStatus.TOO_LONG:
        notes.append(
            f"Output is long for a typical {output_profile.value} ({word_count} words vs target {target_min}-{target_max})."
        )
    if missing_sections:
        notes.append(f"Missing required sections: {', '.join(missing_sections)}.")
    if citation_count < minimum_citations:
        notes.append(
            f"Citation count is light for this format ({citation_count} vs expected minimum {minimum_citations})."
        )
    if bundle.sections.get("investment_recommendation") is None and output_profile != OutputProfile.ONE_PAGER:
        notes.append("Recommendation section is missing or empty.")
    if bundle.evidence_gaps:
        notes.append(f"Evidence gaps remain open: {len(bundle.evidence_gaps)}.")

    if (
        length_status == LengthStatus.TARGET
        and not missing_sections
        and citation_count >= minimum_citations
    ):
        overall_status = ValidationStatus.PASS
    elif section_coverage < 0.6 or citation_count == 0:
        overall_status = ValidationStatus.FAIL
    else:
        overall_status = ValidationStatus.WATCH

    return ReportStandardsAssessment(
        workflow=workflow,
        output_profile=output_profile,
        industry_profile=INDUSTRY_PROFILE_LABELS[(workflow, output_profile)],
        word_count=word_count,
        target_word_range=(target_min, target_max),
        length_status=length_status,
        citation_count=citation_count,
        minimum_citations=minimum_citations,
        required_sections=required_sections,
        present_sections=present_sections,
        missing_sections=missing_sections,
        section_coverage=section_coverage,
        citation_density=round(citation_density, 2),
        overall_status=overall_status,
        notes=notes,
    )
