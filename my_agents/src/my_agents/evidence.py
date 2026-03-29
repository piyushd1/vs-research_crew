from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from my_agents.schemas import (
    AgentFindingResult,
    AuditIssue,
    AuditResult,
    ConflictLevel,
    FindingRecord,
    RiskLevel,
    SourcePriorityConfig,
)


def _normalize_key(finding: FindingRecord) -> str:
    key = finding.claim_key or finding.claim
    return " ".join(key.lower().split())


@dataclass
class EvidenceRegistry:
    source_profile: SourcePriorityConfig
    findings_by_agent: dict[str, AgentFindingResult] = field(default_factory=dict)
    _claims: dict[str, list[FindingRecord]] = field(default_factory=lambda: defaultdict(list))

    def add_result(self, result: AgentFindingResult) -> None:
        self.findings_by_agent[result.agent_name] = result
        for finding in result.findings:
            claim_key = _normalize_key(finding)
            self._claims[claim_key].append(finding)
            self._apply_conflict_status(claim_key)

    def _apply_conflict_status(self, claim_key: str) -> None:
        claim_records = self._claims[claim_key]
        if len(claim_records) < 2:
            return

        distinct_values = {record.claim_value or record.evidence_summary for record in claim_records}
        if len(distinct_values) < 2:
            return

        tiers = [self.source_profile.tiers.get(record.source_type, 99) for record in claim_records]
        highest = min(tiers)
        lowest = max(tiers)
        conflict_level = ConflictLevel.HIGH if highest <= 2 < lowest else ConflictLevel.MEDIUM
        for record in claim_records:
            record.conflict_level = conflict_level

    def findings(self) -> list[FindingRecord]:
        return [
            finding
            for result in self.findings_by_agent.values()
            for finding in result.findings
        ]

    def unique_sources(self) -> list[dict[str, str]]:
        seen: set[tuple[str, str]] = set()
        unique = []
        for finding in self.findings():
            key = (finding.source_ref, finding.source_type)
            if key in seen:
                continue
            seen.add(key)
            unique.append({"source_ref": finding.source_ref, "source_type": finding.source_type})
        return unique

    def summary(self, limit: int = 10) -> str:
        lines: list[str] = []
        for finding in self.findings()[:limit]:
            lines.append(
                f"- {finding.claim} | source={finding.source_ref} | confidence={finding.confidence:.2f}"
            )
        return "\n".join(lines) if lines else "No findings collected yet."

    def deterministic_audit(self, required_citations: bool = True) -> AuditResult:
        issues: list[AuditIssue] = []
        gaps: list[str] = []
        findings_list = self.findings()
        for finding in findings_list:
            if required_citations and not finding.source_ref:
                issues.append(
                    AuditIssue(
                        title="Missing citation",
                        severity=RiskLevel.HIGH,
                        detail=f"Finding '{finding.claim}' is missing a source reference.",
                    )
                )
            if finding.conflict_level != ConflictLevel.NONE:
                issues.append(
                    AuditIssue(
                        title="Conflicting evidence",
                        severity=RiskLevel.HIGH
                        if finding.conflict_level == ConflictLevel.HIGH
                        else RiskLevel.MEDIUM,
                        detail=f"Claim '{finding.claim}' has {finding.conflict_level.value} conflict evidence.",
                        source_refs=[finding.source_ref],
                    )
                )

        if not findings_list:
            gaps.append("No specialist findings were produced.")

        return AuditResult(
            passed=not issues,
            issues=issues,
            gaps=gaps,
        )


def combine_open_questions(results: Iterable[AgentFindingResult]) -> list[str]:
    seen: set[str] = set()
    combined: list[str] = []
    for result in results:
        for question in result.open_questions:
            if question in seen:
                continue
            seen.add(question)
            combined.append(question)
    return combined
