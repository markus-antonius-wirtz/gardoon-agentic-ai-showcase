"""Strict Pydantic v2 domain models for API contracts, vector retrieval, and agent outputs."""

from typing import Literal

from pydantic import BaseModel, Field

DocCategory = Literal["pine_v5_reference", "anti_repainting_audit", "risk_compliance_policy"]
SeverityLevel = Literal["critical", "warning", "info"]
ComplianceVerdict = Literal["COMPLIANT", "REVIEW_REQUIRED", "BLOCKED"]
HumanActionChoice = Literal["approve_with_disclaimer", "tighten_risk_parameters", "reject_publication"]


class KnowledgeDocument(BaseModel):
    """Source document stored in the Qdrant Hybrid Vector Database."""

    doc_id: str
    title: str
    category: DocCategory
    severity: SeverityLevel
    version: str = "2026.4"
    tenant: str = "tradingtackle"
    tags: list[str]
    content: str


class RetrievedChunk(BaseModel):
    """Retrieved document with transparent Dense, Sparse BM25, and RRF scores."""

    doc_id: str
    title: str
    category: DocCategory
    severity: SeverityLevel
    version: str
    tenant: str
    tags: list[str]
    excerpt: str
    dense_score: float = Field(ge=0.0, le=1.0)
    sparse_score: float = Field(ge=0.0, le=1.0)
    rrf_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)


class AuditFinding(BaseModel):
    """Individual audit or compliance finding grounded in a cited knowledge document."""

    rule_id: str = Field(description="Policy or reference ID such as TT-REP-001 or TT-RISK-004")
    severity: SeverityLevel
    title: str
    explanation: str
    cited_doc_id: str
    remediation: str


class StrategyMetrics(BaseModel):
    """Empirical and risk guardrails evaluated for a quantitative strategy."""

    expected_winrate_range: str = Field(description="Realistic range e.g. '48% - 55%'")
    profit_factor_estimate: str = Field(description="Realistic range e.g. '1.45 - 1.85'")
    max_drawdown_est_pct: float = Field(ge=0.0, le=100.0)
    recommended_timeframe: str
    repainting_clean: bool
    commission_slippage_modeled: bool


class FinalAuditReport(BaseModel):
    """Final structured report produced by the Multi-Agent pipeline."""

    strategy_title: str
    executive_summary: str
    compliance_verdict: ComplianceVerdict
    pine_script_v5_code: str
    metrics: StrategyMetrics
    findings: list[AuditFinding]
    cited_doc_ids: list[str]
    correction_loops_executed: int = 0
    human_gate_triggered: bool = False
    human_decision_applied: str | None = None
    model_routing_summary: dict[str, str] = Field(default_factory=dict)


class HumanInterruptPayload(BaseModel):
    """Payload emitted when LangGraph pauses via interrupt() for human governance."""

    thread_id: str
    reason: str
    max_drawdown_est_pct: float
    triggered_policy_ids: list[str]
    draft_summary: str
    draft_code_preview: str
    available_actions: list[dict[str, str]]


class ScenarioPreset(BaseModel):
    """Pre-configured 1-click showcase scenario for enterprise evaluators."""

    id: str
    badge: str
    title: str
    subtitle: str
    highlight_feature: str
    prompt: str
    tenant: str = "tradingtackle"


class RunRequest(BaseModel):
    """Incoming request to execute the Multi-Agent LangGraph pipeline."""

    prompt: str = Field(min_length=12, max_length=2400)
    scenario_id: str | None = None
    tenant: str = Field(default="tradingtackle", pattern=r"^[a-z0-9_-]{2,32}$")
    reasoning_tier: Literal["balanced", "deep"] = "balanced"


class ResumeRunRequest(BaseModel):
    """Human-in-the-Loop decision payload to resume a paused LangGraph checkpoint."""

    action: HumanActionChoice
    reviewer_note: str = Field(default="", max_length=400)


class NaiveComparisonResponse(BaseModel):
    """Side-by-side comparison between a single ungrounded LLM call and the Multi-Agent graph."""

    naive_model: str
    naive_output: str
    missed_risks: list[str]
    latency_ms: int
    why_multi_agent_wins: list[str]


class SystemTelemetry(BaseModel):
    """Live container, Kubernetes, and Vector DB health metadata exposed in the Glass-Box UI."""

    status: Literal["healthy", "degraded"]
    pod_name: str
    namespace: str
    node_name: str
    cluster_topology: str
    python_version: str
    qdrant_mode: str
    qdrant_collection: str
    indexed_documents: int
    vector_dimensions: int
    hybrid_fusion: str
    checkpointer_backend: str
    uptime_seconds: int
    models_configured: dict[str, str]
    rate_limit_per_hour: int
