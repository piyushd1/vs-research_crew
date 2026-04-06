from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkflowType(StrEnum):
    SOURCING = "sourcing"
    DUE_DILIGENCE = "due_diligence"
    PORTFOLIO = "portfolio"


class OutputProfile(StrEnum):
    IC_MEMO = "ic_memo"
    FULL_REPORT = "full_report"
    ONE_PAGER = "one_pager"


class ApproveMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class LLMProvider(StrEnum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class PrivacyTag(StrEnum):
    PUBLIC = "public"
    UPLOADED_PRIVATE = "uploaded_private"
    DERIVED_SENSITIVE = "derived_sensitive"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConflictLevel(StrEnum):
    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    SKIP = "skip"
    ABORT = "abort"


class LengthStatus(StrEnum):
    TOO_SHORT = "too_short"
    TARGET = "target"
    TOO_LONG = "too_long"


class ValidationStatus(StrEnum):
    PASS = "pass"
    WATCH = "watch"
    FAIL = "fail"


ALLOWED_SECTION_KEYS = {
    "executive_summary",
    "company_snapshot",
    "market_landscape",
    "financial_analysis",
    "product_technology",
    "founder_assessment",
    "gtm_momentum",
    "regulatory_compliance",
    "risk_register",
    "portfolio_health",
    "support_recommendations",
    "investment_recommendation",
    "scorecard_summary",
    "top_signals",
    "top_risks",
    "open_questions",
    "evidence_gaps",
    "next_steps",
}


class LLMConfig(BaseModel):
    provider: LLMProvider
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    open_source_only: bool = True
    allow_closed_models: bool = False
    allowed_model_prefixes: list[str] = Field(
        default_factory=lambda: [
            "deepseek/",
            "openrouter/deepseek/",
            "meta-llama/",
            "openrouter/meta-llama/",
            "llama-",
            "mistral/",
            "openrouter/mistral/",
            "mixtral",
            "qwen/",
            "openrouter/qwen/",
            "gemma",
            "openrouter/google/gemma",
            "granite",
            "phi-",
            "falcon",
            "olmo",
            "nemotron",
        ]
    )
    synthesis_model: str | None = None
    eval_model: str | None = None


class LinearConfig(BaseModel):
    enabled: bool = False
    team_id: str | None = None
    project_id: str | None = None
    label_ids: list[str] = Field(default_factory=list)


class IntegrationsConfig(BaseModel):
    linear: LinearConfig = Field(default_factory=LinearConfig)


class Brief(BaseModel):
    company_name: str
    website: str = "Unknown"
    sector: str = "general"
    stage: str = "unknown"
    geography: str = "India"
    one_line: str | None = None
    investment_thesis: str | None = None
    questions: list[str] = Field(default_factory=list)
    docs_dir: str | None = None
    notes: str | None = None
    focus_instructions: str | None = None
    exclude_instructions: str | None = None

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, data: dict) -> dict:
        if isinstance(data, dict):
            if data.get("sector") is None:
                data["sector"] = "general"
            if data.get("stage") is None:
                data["stage"] = "unknown"
            if data.get("geography") is None:
                data["geography"] = "India"
            if data.get("website") is None:
                data["website"] = "Unknown"
        return data

    @field_validator("docs_dir")
    @classmethod
    def validate_docs_dir(cls, value: str | None) -> str | None:
        if value is None:
            return value
        docs_path = Path(value)
        if not docs_path.exists():
            raise ValueError(f"docs_dir does not exist: {value}")
        allowed_suffixes = {".pdf", ".csv"}
        ignored_filenames = {".ds_store"}
        unsupported = sorted(
            str(path.relative_to(docs_path))
            for path in docs_path.rglob("*")
            if path.is_file()
            and path.name.lower() not in ignored_filenames
            and path.suffix.lower() not in allowed_suffixes
        )
        if unsupported:
            raise ValueError(
                "docs_dir only supports PDF and CSV files in v1. Unsupported files: "
                + ", ".join(unsupported[:10])
            )
        return value


class DownstreamFlag(BaseModel):
    flag: str
    for_agent: str
    detail: str


class FindingRecord(BaseModel):
    claim: str
    evidence_summary: str
    source_ref: str
    source_type: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    open_questions: list[str] = Field(default_factory=list)
    claim_key: str | None = None
    claim_value: str | None = None
    privacy_tag: PrivacyTag = PrivacyTag.PUBLIC
    conflict_level: ConflictLevel = ConflictLevel.NONE


class SourceAccessRecord(BaseModel):
    source_name: str
    source_type: str
    accessed: bool
    note: str | None = None


class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    rationale: str


class AgentFindingResult(BaseModel):
    agent_name: str
    summary: str
    findings: list[FindingRecord]
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    downstream_flags: list[DownstreamFlag] = Field(default_factory=list)
    sources_checked: list[SourceAccessRecord] = Field(default_factory=list)
    suggested_section_keys: list[str] = Field(default_factory=list)
    partial: bool = False


class AuditIssue(BaseModel):
    title: str
    severity: RiskLevel
    detail: str
    source_refs: list[str] = Field(default_factory=list)


class AuditResult(BaseModel):
    auditor: str = "evidence_auditor"
    passed: bool
    issues: list[AuditIssue] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ScorecardDimension(BaseModel):
    dimension: str
    weight: int
    score: int = Field(ge=1, le=5)
    rationale: str
    evidence_count: int = 0
    average_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    method: str = "weighted_evidence_model"


class ScorecardSummary(BaseModel):
    overall_score: float = Field(ge=0.0, le=100.0)
    recommendation: str
    dimensions: list[ScorecardDimension] = Field(default_factory=list)
    weighted_dimension_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence_index: float = Field(default=0.0, ge=0.0, le=100.0)
    coverage_index: float = Field(default=0.0, ge=0.0, le=100.0)
    conflict_index: float = Field(default=0.0, ge=0.0, le=100.0)
    gap_penalty: float = Field(default=0.0, ge=0.0, le=100.0)
    audit_penalty: float = Field(default=0.0, ge=0.0, le=100.0)
    methodology: str = (
        "Workflow-aware weighted score using specialist ratings adjusted for evidence confidence, "
        "coverage, conflicts, and diligence gaps."
    )


class FindingsBundle(BaseModel):
    company_name: str
    workflow: WorkflowType
    summary: str
    sections: dict[str, str]
    scorecard: ScorecardSummary
    top_signals: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReportStandardsAssessment(BaseModel):
    workflow: WorkflowType
    output_profile: OutputProfile
    industry_profile: str
    word_count: int = Field(ge=0)
    target_word_range: tuple[int, int]
    length_status: LengthStatus = LengthStatus.TARGET
    citation_count: int = Field(ge=0)
    minimum_citations: int = Field(ge=0)
    required_sections: list[str] = Field(default_factory=list)
    present_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    section_coverage: float = Field(ge=0.0, le=1.0)
    citation_density: float = Field(ge=0.0)
    overall_status: ValidationStatus = ValidationStatus.WATCH
    notes: list[str] = Field(default_factory=list)


class WorkflowTaskDefinition(BaseModel):
    agent: str
    objective: str
    checkpoint: bool = False

class FindingEval(BaseModel):
    finding_claim: str
    is_hallucination: bool
    rationale: str

class VCRubric(BaseModel):
    relevance_score: int = Field(ge=1, le=10)
    tone_score: int = Field(ge=1, le=10)
    citation_quality_score: int = Field(default=7, ge=1, le=10)
    structure_score: int = Field(default=7, ge=1, le=10)
    length_fit_score: int = Field(default=7, ge=1, le=10)
    evidence_strength_score: int = Field(default=7, ge=1, le=10)
    actionability_score: int = Field(default=7, ge=1, le=10)
    hallucinations: list[FindingEval] = Field(default_factory=list)
    negative_constraint_violations: list[str] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)
    final_eval_score: int = Field(default=0, ge=0, le=100)
    summary_feedback: str

class WorkflowConfig(BaseModel):
    workflow: WorkflowType
    description: str
    tasks: list[WorkflowTaskDefinition]


class AgentSpec(BaseModel):
    role: str
    goal: str
    backstory: str
    prompt_notes: list[str] = Field(default_factory=list)
    source_focus: list[str] = Field(default_factory=list)
    scoring_dimensions: list[str] = Field(default_factory=list)
    default_tools: list[str] = Field(default_factory=list)
    allow_delegation: bool = False
    active: bool = True
    failure_guidance: str | None = None


class OutputProfileConfig(BaseModel):
    profile: OutputProfile
    title: str
    format: str
    sections: list[str]

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[str]) -> list[str]:
        invalid = [section for section in value if section not in ALLOWED_SECTION_KEYS]
        if invalid:
            raise ValueError(f"Unsupported section keys: {invalid}")
        return value


class SourcePriorityConfig(BaseModel):
    profile: str
    tiers: dict[str, int]
    india_priority_sources: list[str] = Field(default_factory=list)
    founder_signal_sources: list[str] = Field(default_factory=list)
    search_provider: str | None = None


class CompletedAgentState(BaseModel):
    agent_name: str
    completed_at: datetime


class RunState(BaseModel):
    workflow: WorkflowType
    output_profile: OutputProfile
    company_name: str
    completed_agents: list[CompletedAgentState] = Field(default_factory=list)
    pending_agents: list[str] = Field(default_factory=list)
    findings: dict[str, AgentFindingResult] = Field(default_factory=dict)
    pending_flags: list[DownstreamFlag] = Field(default_factory=list)
    checkpoint_history: dict[str, ApprovalAction] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunRequest(BaseModel):
    workflow: WorkflowType | None = None
    brief_path: Path | None = None
    output_profile: OutputProfile = OutputProfile.IC_MEMO
    approve_mode: ApproveMode = ApproveMode.AUTO
    website: str | None = None
    sector: str | None = None
    stage: str | None = None
    geography: str | None = None
    docs_dir: str | None = None
    sources_profile: str | None = None
    resume: Path | None = None
    config_dir: Path | None = None
    verbose: bool = False
    company_name: str | None = None
    focus_instructions: str | None = None
    exclude_instructions: str | None = None
    run_evals: bool = False
    eval_only_dir: Path | None = None

    @model_validator(mode="after")
    def validate_run_request(self) -> RunRequest:
        if self.resume is None and self.eval_only_dir is None:
            has_brief = self.brief_path is not None
            has_company = self.company_name is not None
            if not has_brief and not has_company:
                raise ValueError(
                    "Either --brief or --company is required unless --resume or --eval-only-dir is used."
                )
            if self.workflow is None:
                self.workflow = WorkflowType.SOURCING
        return self


class RunArtifacts(BaseModel):
    run_dir: Path
    report_path: Path
    scorecard_path: Path
    sources_path: Path
    run_state_path: Path
    bundle_path: Path
    pdf_path: Path | None = None
    one_pager_path: Path | None = None
    report_html_path: Path | None = None
    eval_path: Path | None = None
    eval_report_path: Path | None = None
    eval_report_html_path: Path | None = None
    eval_prompt_path: Path | None = None
    standards_path: Path | None = None
    standards_html_path: Path | None = None
