export type DocCategory =
  | 'pine_v5_reference'
  | 'anti_repainting_audit'
  | 'risk_compliance_policy';

export type SeverityLevel = 'critical' | 'warning' | 'info';
export type ComplianceVerdict = 'COMPLIANT' | 'REVIEW_REQUIRED' | 'BLOCKED';
export type HumanActionChoice =
  | 'tighten_risk_parameters'
  | 'approve_with_disclaimer'
  | 'reject_publication';

export interface RetrievedChunk {
  doc_id: string;
  title: string;
  category: DocCategory;
  severity: SeverityLevel;
  version: string;
  tenant: string;
  tags: string[];
  excerpt: string;
  dense_score: number;
  sparse_score: number;
  rrf_score: number;
  rank: number;
}

export interface AuditFinding {
  rule_id: string;
  severity: SeverityLevel;
  title: string;
  explanation: string;
  cited_doc_id: string;
  remediation: string;
}

export interface StrategyMetrics {
  expected_winrate_range: string;
  profit_factor_estimate: string;
  max_drawdown_est_pct: number;
  recommended_timeframe: string;
  repainting_clean: boolean;
  commission_slippage_modeled: boolean;
}

export interface FinalAuditReport {
  strategy_title: string;
  executive_summary: string;
  compliance_verdict: ComplianceVerdict;
  pine_script_v5_code: string;
  metrics: StrategyMetrics;
  findings: AuditFinding[];
  cited_doc_ids: string[];
  correction_loops_executed: number;
  human_gate_triggered: boolean;
  human_decision_applied: string | null;
  model_routing_summary: Record<string, string>;
}

export interface HumanInterruptPayload {
  thread_id: string;
  reason: string;
  max_drawdown_est_pct: number;
  triggered_policy_ids: string[];
  draft_summary: string;
  draft_code_preview: string;
  available_actions: Array<{
    id: HumanActionChoice;
    label: string;
    description: string;
  }>;
}

export interface ScenarioPreset {
  id: string;
  badge: string;
  title: string;
  subtitle: string;
  highlight_feature: string;
  prompt: string;
  tenant: string;
}

export interface TraceStep {
  node: string;
  model_used: string;
  latency_ms: number;
  detail: string;
  loop_iteration: number;
  cost_usd_est: number;
}

export interface NaiveComparisonResponse {
  naive_model: string;
  naive_output: string;
  missed_risks: string[];
  latency_ms: number;
  why_multi_agent_wins: string[];
}

export interface SystemTelemetry {
  status: 'healthy' | 'degraded';
  pod_name: string;
  namespace: string;
  node_name: string;
  cluster_topology: string;
  python_version: string;
  qdrant_mode: string;
  qdrant_collection: string;
  indexed_documents: number;
  vector_dimensions: number;
  hybrid_fusion: string;
  checkpointer_backend: string;
  uptime_seconds: number;
  models_configured: Record<string, string>;
  rate_limit_per_hour: number;
}
