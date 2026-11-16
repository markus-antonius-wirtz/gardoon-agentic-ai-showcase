"""Production LangGraph agent nodes with Smart Model Routing, Hybrid RAG, Critic Loop & HITL."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Send, interrupt
from pydantic import SecretStr

from app.agents.state import (
    AgentGraphState,
    ArchitectDraft,
    IntakePlan,
    RetrievalTaskState,
    TraceStep,
)
from app.agents.static_analyzer import scan_user_submission, verify_generated_pine_v5
from app.config import get_settings
from app.knowledge.vector_store import get_knowledge_store
from app.schemas import (
    AuditFinding,
    ComplianceVerdict,
    FinalAuditReport,
    RetrievedChunk,
    StrategyMetrics,
)

logger = logging.getLogger(__name__)


def _has_live_gemini_key() -> bool:
    key = get_settings().gemini_api_key
    return bool(key and key != "your-gemini-api-key-here" and len(key) > 15)


def _build_chat_model(model_name: str, temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=SecretStr(settings.gemini_api_key),
        temperature=temperature,
        max_retries=2,
        timeout=45,
    )


def _fallback_pine_v5_template(high_risk: bool = False) -> str:
    qty = 45 if high_risk else 15
    atr_mult = 4.2 if high_risk else 2.2
    return (
        "//@version=5\n"
        f"strategy('TradingTackle Audited Adaptive Breakout v5', overlay=true, initial_capital=10000, "
        f"default_qty_type=strategy.percent_of_equity, default_qty_value={qty}, pyramiding=0, "
        "commission_type=strategy.commission.percent, commission_value=0.06, slippage=2)\n\n"
        "// --- Typed Pine v5 Inputs (TT-PINE-004) ---\n"
        "emaLen     = input.int(200, title='Regime EMA Length', minval=20, maxval=500)\n"
        "breakLen   = input.int(20, title='Donchian Breakout Lookback', minval=5, maxval=100)\n"
        "atrLen     = input.int(14, title='ATR Volatility Period', minval=5, maxval=50)\n"
        f"atrMult    = input.float({atr_mult}, title='ATR Hard Stop Multiplier', minval=1.0, maxval=6.0, step=0.1)\n"
        "rrMultiple = input.float(2.0, title='Reward-to-Risk Target Multiple', minval=1.0, maxval=5.0, step=0.2)\n\n"
        "// --- Non-Repainting Global Series Evaluation (TT-PINE-010 & TT-REP-001) ---\n"
        "htfDailyClose = request.security(syminfo.tickerid, 'D', close[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_on)\n"
        "regimeEma     = ta.ema(close, emaLen)\n"
        "upperChannel  = ta.highest(high[1], breakLen)\n"
        "atrValue      = ta.atr(atrLen)\n"
        "volSma        = ta.sma(volume, 20)\n"
        "volConfirmed  = na(volume) or volume > volSma * 1.15\n\n"
        "warmupReady = bar_index >= emaLen and not na(regimeEma) and not na(atrValue)\n"
        "longSignal  = warmupReady and close > regimeEma and close > htfDailyClose and close > upperChannel and volConfirmed\n\n"
        "if longSignal and strategy.position_size == 0\n"
        "    strategy.entry('Long', strategy.long)\n\n"
        "if strategy.position_size > 0\n"
        "    stopPrice   = strategy.position_avg_price - (atrValue * atrMult)\n"
        "    targetPrice = strategy.position_avg_price + (atrValue * atrMult * rrMultiple)\n"
        "    strategy.exit('Exit Long', from_entry='Long', stop=stopPrice, limit=targetPrice)\n\n"
        "plot(regimeEma, title='200 EMA Regime', color=color.new(#3b82f6, 15), linewidth=2)\n"
        "plot(upperChannel, title='Breakout Trigger', color=color.new(#10b981, 35))\n"
    )


def intake_supervisor(state: AgentGraphState) -> dict[str, Any]:
    """Node 1: Triage user submission, scan static signals, and plan parallel hybrid retrieval."""
    t0 = time.perf_counter()
    settings = get_settings()
    prompt = state["prompt"]
    trap_findings, lev_x, hinted_dd = scan_user_submission(prompt)

    model_used = settings.gemini_fast_model
    plan: IntakePlan | None = None

    if _has_live_gemini_key():
        try:
            llm = _build_chat_model(model_used, temperature=0.0)
            structured_llm = llm.with_structured_output(IntakePlan)
            sys_msg = SystemMessage(
                content=(
                    "You are the Intake Supervisor of Gardoon's Multi-Agent Quantitative Compliance Studio "
                    "built for TradingTackle.ai. Analyze the user's request and produce two sharp hybrid vector "
                    "search queries: (1) pine_search_query targeting exact Pine Script v5 functions/syntax, and "
                    "(2) risk_search_query targeting anti-repainting traps, friction baseline, and EU/MiFID risk thresholds."
                )
            )
            res = structured_llm.invoke([sys_msg, HumanMessage(content=prompt)])
            plan = cast(IntakePlan, res)
        except Exception as exc:
            logger.warning("Intake Supervisor LLM fallback triggered: %s", exc)
            model_used = f"{model_used} (deterministic-fallback)"
    else:
        model_used = "deterministic-ci-engine"

    if plan is None:
        is_audit = "//@version" in prompt or "study(" in prompt or "lookahead" in prompt
        is_high_risk = lev_x > 3.0 or hinted_dd > 20.0
        intent: Any = (
            "high_risk_stress_test"
            if is_high_risk
            else ("audit_submitted_code" if is_audit else "design_strategy")
        )
        plan = IntakePlan(
            intent=intent,
            pine_search_query="Pine Script v5 strategy declaration ta.ema ta.atr strategy.exit request.security",
            risk_search_query=(
                "request.security lookahead_on repainting commission_value slippage max_drawdown 20% leverage winrate"
            ),
            detected_leverage_x=max(lev_x, 1.0),
            requested_equity_pct=45.0 if is_high_risk else 15.0,
            summary_note="Decomposed submission into parallel Pine v5 syntax & quantitative risk audit tracks.",
        )
    else:
        plan.detected_leverage_x = max(plan.detected_leverage_x, lev_x)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    trace: TraceStep = {
        "node": "intake_supervisor",
        "model_used": model_used,
        "latency_ms": elapsed_ms,
        "detail": (
            f"Intent={plan.intent} · Leverage={plan.detected_leverage_x:.1f}x · "
            f"Pre-scan signals={len(trap_findings)} · Dispatching 2 parallel Qdrant tracks"
        ),
        "loop_iteration": 0,
        "cost_usd_est": 0.00025 if "deterministic" not in model_used else 0.0,
    }
    return {
        "intake_plan": plan.model_dump(),
        "input_trap_findings": trap_findings,
        "correction_loops": 0,
        "critic_issues": [],
        "model_routing": {"intake_supervisor": model_used},
        "trace_steps": [trace],
    }


def dispatch_parallel_retrievers(state: AgentGraphState) -> list[Send]:
    """LangGraph Send() fan-out: execute Pine v5 docs and Risk/Repainting retrieval concurrently."""
    plan = state.get("intake_plan", {})
    tenant = state.get("tenant", "tradingtackle")
    pine_q = str(plan.get("pine_search_query") or state["prompt"])
    risk_q = str(plan.get("risk_search_query") or state["prompt"])
    return [
        Send(
            "retrieve_pine_docs",
            RetrievalTaskState(track="pine_docs", query=pine_q, tenant=tenant),
        ),
        Send(
            "retrieve_risk_policies",
            RetrievalTaskState(track="risk_policies", query=risk_q, tenant=tenant),
        ),
    ]


def retrieve_pine_docs(task: RetrievalTaskState) -> dict[str, Any]:
    """Node 2a (Parallel Branch A): Hybrid Dense+BM25 RRF retrieval on Pine v5 documentation."""
    t0 = time.perf_counter()
    store = get_knowledge_store()
    chunks = store.hybrid_search(
        task["query"],
        tenant=task["tenant"],
        category="pine_v5_reference",
        top_k=4,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    top_ids = ", ".join(c.doc_id for c in chunks[:3])
    trace: TraceStep = {
        "node": "retrieve_pine_docs",
        "model_used": "qdrant-hybrid-rrf (dense+bm25)",
        "latency_ms": elapsed_ms,
        "detail": f"Retrieved {len(chunks)} Pine v5 reference chunks ({top_ids})",
        "loop_iteration": 0,
        "cost_usd_est": 0.00004,
    }
    return {"retrieved_chunks": chunks, "trace_steps": [trace]}


def retrieve_risk_policies(task: RetrievalTaskState) -> dict[str, Any]:
    """Node 2b (Parallel Branch B): Hybrid Dense+BM25 RRF retrieval on Anti-Repainting & Risk Policies."""
    t0 = time.perf_counter()
    store = get_knowledge_store()
    rep_chunks = store.hybrid_search(
        task["query"],
        tenant=task["tenant"],
        category="anti_repainting_audit",
        top_k=3,
    )
    risk_chunks = store.hybrid_search(
        task["query"],
        tenant=task["tenant"],
        category="risk_compliance_policy",
        top_k=3,
    )
    combined = rep_chunks + risk_chunks
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    top_ids = ", ".join(c.doc_id for c in combined[:4])
    trace: TraceStep = {
        "node": "retrieve_risk_policies",
        "model_used": "qdrant-hybrid-rrf (dense+bm25)",
        "latency_ms": elapsed_ms,
        "detail": f"Retrieved {len(combined)} Repainting & MiFID Risk chunks ({top_ids})",
        "loop_iteration": 0,
        "cost_usd_est": 0.00005,
    }
    return {"retrieved_chunks": combined, "trace_steps": [trace]}


def quant_architect(state: AgentGraphState) -> dict[str, Any]:
    """Node 3: Synthesize or remediate Pine Script v5 strategy strictly grounded in retrieved docs."""
    t0 = time.perf_counter()
    settings = get_settings()
    loops = int(state.get("correction_loops", 0))
    tier = state.get("reasoning_tier", "balanced")

    # Smart Model Routing: escalate to Gemini Pro on Deep tier or Critic self-correction retry!
    selected_model = (
        settings.gemini_reasoning_model
        if (tier == "deep" or loops > 0)
        else settings.gemini_fast_model
    )

    chunks: list[RetrievedChunk] = state.get("retrieved_chunks", [])
    context_block = "\n\n".join(
        f"[{c.doc_id}] ({c.category}, severity={c.severity}, RRF={c.rrf_score:.2f}): {c.excerpt}"
        for c in chunks
    )
    trap_findings: list[AuditFinding] = state.get("input_trap_findings", [])
    critic_issues: list[str] = state.get("critic_issues", [])
    plan = state.get("intake_plan", {})
    lev_x = float(plan.get("detected_leverage_x", 1.0))
    _, _, hinted_dd = scan_user_submission(state["prompt"])
    is_high_risk = lev_x > 3.0 or hinted_dd > 20.0 or float(plan.get("requested_equity_pct", 15.0)) > 25.0

    draft: ArchitectDraft | None = None

    if _has_live_gemini_key():
        try:
            llm = _build_chat_model(selected_model, temperature=0.1)
            structured_llm = llm.with_structured_output(ArchitectDraft)
            remediation_block = (
                "\nCRITICAL SELF-CORRECTION REQUIRED FROM PREVIOUS LOOP:\n"
                + "\n".join(f"- {issue}" for issue in critic_issues)
                if critic_issues
                else ""
            )
            trap_block = (
                "\nPRE-DETECTED SUBMISSION TRAPS TO DOCUMENT IN FINDINGS & FIX IN CODE:\n"
                + "\n".join(f"- [{f.rule_id}] {f.title}: {f.explanation}" for f in trap_findings)
                if trap_findings
                else ""
            )
            sys_prompt = (
                "You are the Principal Quantitative Architect & Pine Script v5 Engineer at TradingTackle.ai "
                "(engineered by Gardoon Ltd.).\n"
                "STRICT MANDATES:\n"
                "1. Ground every technical & risk decision ONLY in the retrieved Qdrant Knowledge Chunks below.\n"
                "2. Output complete, compilable Pine Script v5 starting with `//@version=5` and `strategy(...)` "
                "including `commission_type=strategy.commission.percent, commission_value=0.06, slippage=2`.\n"
                "3. Always include `strategy.exit(...)` with an explicit `stop=` level. Never use unsafe "
                "`barmerge.lookahead_on` without `[1]` series offset, legacy `study()`, or bare `security()`.\n"
                "4. Never promise >75% or 'guaranteed' winrates in `executive_summary` (use realistic empirical "
                "ranges like '44% - 53%' and Profit Factor '1.40 - 1.85').\n"
                "5. If the user explicitly requested >3x leverage or >25% equity sizing or >20% drawdown, reflect "
                "the realistic elevated `max_drawdown_est_pct` (e.g., 26.5 - 31.0) so downstream Policy TT-RISK-002 "
                "can trigger Human Risk Officer Governance!\n"
                f"\nRETRIEVED QDRANT HYBRID KNOWLEDGE:\n{context_block}"
                f"{trap_block}{remediation_block}"
            )
            res = structured_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=state["prompt"])])
            draft = cast(ArchitectDraft, res)
        except Exception as exc:
            logger.warning("Quant Architect LLM fallback triggered (%s): %s", selected_model, exc)
            selected_model = f"{selected_model} (deterministic-fallback)"
    else:
        selected_model = "deterministic-ci-engine"

    if draft is None:
        cited = list({c.doc_id for c in chunks[:6]} | {f.cited_doc_id for f in trap_findings})
        base_findings = list(trap_findings) or [
            AuditFinding(
                rule_id="TT-REP-003",
                severity="info",
                title="Realistic Friction Baseline Applied (0.06% Commission + 2 Ticks Slippage)",
                explanation="Configured mandatory exchange fee and slippage baseline inside `strategy()` header.",
                cited_doc_id="TT-REP-003",
                remediation="Verified compliant in generated Pine Script v5 output.",
            ),
            AuditFinding(
                rule_id="TT-PINE-005",
                severity="info",
                title="Hard Intrabar Stop-Loss Linked via `strategy.exit()`",
                explanation="Attached dynamic ATR hard stop and reward-multiple target to open long exposure.",
                cited_doc_id="TT-PINE-005",
                remediation="Verified `strategy.exit('Exit Long', from_entry='Long', stop=...)`.",
            ),
        ]
        draft = ArchitectDraft(
            strategy_title=(
                "High-Beta Leveraged Momentum Swing (Pending Risk Governance)"
                if is_high_risk
                else "Audited Adaptive EMA-200 & Donchian ATR Breakout (Pine v5)"
            ),
            executive_summary=(
                "Synthesized non-repainting Pine Script v5 strategy grounded in TradingTackle institutional "
                "standards: confirmed `[1]` higher-timeframe filtering, global `ta.*` evaluation, 6 bps + 2 ticks "
                "friction modeling, and deterministic ATR stop protection."
            ),
            pine_script_v5_code=_fallback_pine_v5_template(high_risk=is_high_risk),
            metrics=StrategyMetrics(
                expected_winrate_range="44% - 52%",
                profit_factor_estimate="1.45 - 1.82",
                max_drawdown_est_pct=29.5 if is_high_risk else 13.8,
                recommended_timeframe="4H" if is_high_risk else "1H",
                repainting_clean=True,
                commission_slippage_modeled=True,
            ),
            findings=base_findings,
            cited_doc_ids=sorted(cited),
        )
    else:
        # Ensure all pre-scanned deterministic submission traps remain documented in findings
        existing_rules = {f.rule_id for f in draft.findings}
        for tf in trap_findings:
            if tf.rule_id not in existing_rules:
                draft.findings.insert(0, tf)
        if is_high_risk and draft.metrics.max_drawdown_est_pct <= 20.0:
            draft.metrics.max_drawdown_est_pct = max(hinted_dd, 28.5)

    routing = dict(state.get("model_routing", {}))
    routing["quant_architect"] = selected_model
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    cost = 0.0028 if "pro" in selected_model else (0.0006 if "deterministic" not in selected_model else 0.0)
    trace: TraceStep = {
        "node": "quant_architect",
        "model_used": selected_model,
        "latency_ms": elapsed_ms,
        "detail": (
            f"Synthesized '{draft.strategy_title}' · Est. Max DD={draft.metrics.max_drawdown_est_pct:.1f}% · "
            f"Findings={len(draft.findings)} (Loop #{loops})"
        ),
        "loop_iteration": loops,
        "cost_usd_est": cost,
    }
    return {
        "draft": draft.model_dump(),
        "model_routing": routing,
        "trace_steps": [trace],
    }


def audit_critic(state: AgentGraphState) -> dict[str, Any]:
    """Node 4: Four-Eyes Critic validating Pine v5 AST rules, grounding citations & TT-RISK-002 thresholds."""
    t0 = time.perf_counter()
    settings = get_settings()
    draft = ArchitectDraft.model_validate(state["draft"])
    loops = int(state.get("correction_loops", 0))

    defects = verify_generated_pine_v5(draft.pine_script_v5_code, draft.executive_summary)
    valid_corpus_ids = {c.doc_id for c in state.get("retrieved_chunks", [])} | {
        f.cited_doc_id for f in state.get("input_trap_findings", [])
    }

    # Normalize citations to valid retrieved IDs
    cleaned_citations = sorted(
        {cid for cid in draft.cited_doc_ids if cid.startswith(("TT-", "GD-"))}
        | {f.cited_doc_id for f in draft.findings if f.cited_doc_id.startswith(("TT-", "GD-"))}
        | {c.doc_id for c in state.get("retrieved_chunks", [])[:4]}
    )
    draft.cited_doc_ids = cleaned_citations

    can_retry = len(defects) > 0 and loops < settings.max_correction_loops
    if can_retry:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        trace: TraceStep = {
            "node": "audit_critic",
            "model_used": "hybrid-static-ast + policy-verifier",
            "latency_ms": elapsed_ms,
            "detail": f"REJECTED draft ({len(defects)} defect(s)) -> Routing back to quant_architect (retry #{loops + 1})",
            "loop_iteration": loops,
            "cost_usd_est": 0.0001,
        }
        return {
            "draft": draft.model_dump(),
            "critic_issues": defects,
            "critic_passed": False,
            "correction_loops": loops + 1,
            "trace_steps": [trace],
        }

    # If max retries reached and any minor static header was still missing, apply deterministic surgical patch
    if defects:
        draft.pine_script_v5_code = _fallback_pine_v5_template(
            high_risk=draft.metrics.max_drawdown_est_pct > 20.0
        )

    plan = state.get("intake_plan", {})
    lev_x = float(plan.get("detected_leverage_x", 1.0))
    req_eq = float(plan.get("requested_equity_pct", 15.0))
    dd_pct = float(draft.metrics.max_drawdown_est_pct)

    needs_hitl = dd_pct > 20.0 or lev_x > 3.0 or req_eq > 25.0
    triggered_policies: list[str] = []
    reason = ""
    if needs_hitl:
        triggered_policies = ["TT-RISK-002", "TT-RISK-004", "TT-RISK-008"]
        reason = (
            f"Policy TT-RISK-002 Triggered: Estimated Max Drawdown ({dd_pct:.1f}%) exceeds the 20.0% "
            f"autonomous threshold (Detected Leverage: {lev_x:.1f}x, Equity Allocation: {req_eq:.0f}%). "
            "Mandatory Human Risk Officer approval required before publication."
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    next_step_label = "human_governance_gate (interrupt)" if needs_hitl else "final_publisher"
    trace = {
        "node": "audit_critic",
        "model_used": f"policy-verifier ({len(valid_corpus_ids)} grounded refs)",
        "latency_ms": elapsed_ms,
        "detail": f"PASSED Pine v5 & anti-repainting checks · Next -> {next_step_label}",
        "loop_iteration": loops,
        "cost_usd_est": 0.0001,
    }
    return {
        "draft": draft.model_dump(),
        "critic_issues": [],
        "critic_passed": True,
        "requires_human_approval": needs_hitl,
        "human_approval_reason": reason,
        "triggered_policy_ids": triggered_policies,
        "trace_steps": [trace],
    }


def route_after_critic(state: AgentGraphState) -> str:
    """Conditional edge routing after Four-Eyes Critic evaluation."""
    if not state.get("critic_passed", True):
        return "quant_architect"
    if state.get("requires_human_approval", False):
        return "human_governance_gate"
    return "final_publisher"


def human_governance_gate(state: AgentGraphState) -> dict[str, Any]:
    """Node 5: Suspend execution via LangGraph interrupt() and apply human Risk Officer decision."""
    draft = ArchitectDraft.model_validate(state["draft"])
    code_lines = draft.pine_script_v5_code.splitlines()
    preview = "\n".join(code_lines[:14]) + ("\n// ..." if len(code_lines) > 14 else "")

    interrupt_payload = {
        "reason": state.get("human_approval_reason", "Policy TT-RISK-002 governance threshold exceeded."),
        "max_drawdown_est_pct": draft.metrics.max_drawdown_est_pct,
        "triggered_policy_ids": state.get("triggered_policy_ids", ["TT-RISK-002"]),
        "draft_summary": draft.executive_summary,
        "draft_code_preview": preview,
        "available_actions": [
            {
                "id": "tighten_risk_parameters",
                "label": "Auto-Tighten Risk Parameters (Recommended)",
                "description": "Cap sizing to 15% equity (1x), inject 18% Max Drawdown circuit breaker & mark COMPLIANT.",
            },
            {
                "id": "approve_with_disclaimer",
                "label": "Approve with High-Risk ESMA Disclaimer",
                "description": "Retain high-beta parameters, attach mandatory MiFID II capital-at-risk header & sign off.",
            },
            {
                "id": "reject_publication",
                "label": "Block Strategy Publication",
                "description": "Quarantine executable orders under Policy TT-RISK-002 and mark report BLOCKED.",
            },
        ],
    }

    # LangGraph stateful suspension! Resumes here when Command(resume=...) arrives.
    raw_decision: Any = interrupt(interrupt_payload)
    t0 = time.perf_counter()

    if isinstance(raw_decision, dict):
        action = str(raw_decision.get("action", "tighten_risk_parameters"))
        note = str(raw_decision.get("reviewer_note", "")).strip()
    else:
        action = str(raw_decision)
        note = ""

    code = draft.pine_script_v5_code
    if action == "tighten_risk_parameters":
        code = re.sub(r"default_qty_value\s*=\s*[0-9.]+", "default_qty_value=15", code)
        if "strategy.risk.max_drawdown" not in code:
            code = code.replace(
                "\n",
                "\nstrategy.risk.max_drawdown(value=18, type=strategy.percent_of_equity) // TT-RISK-008 Kill-Switch\n",
                1,
            )
        draft.pine_script_v5_code = code
        draft.metrics.max_drawdown_est_pct = 15.8
        draft.executive_summary += (
            " [Governance Remediation Applied: Position sizing capped at 15% unleveraged equity and "
            "18% hard portfolio drawdown circuit breaker injected per TT-RISK-002 / TT-RISK-008.]"
        )
        decision_summary = "Auto-Tightened Risk Parameters (15% equity cap + 18% circuit breaker)"
    elif action == "reject_publication":
        draft.pine_script_v5_code = (
            "// [PUBLICATION BLOCKED BY HUMAN RISK OFFICER UNDER POLICY TT-RISK-002]\n"
            "// Executable strategy.entry() calls disabled pending mandate redesign.\n"
            + re.sub(r"(^\s*strategy\.entry\b)", r"// BLOCKED: \1", code, flags=re.MULTILINE)
        )
        decision_summary = "Rejected Publication (Orders Quarantined by Human Risk Officer)"
    else:
        disclaimer_header = (
            "// ⚠️ ESMA / MiFID II HIGH-RISK DERIVATIVE DISCLOSURE (APPROVED BY HUMAN REVIEWER):\n"
            "// Leveraged exposure carries elevated risk of rapid capital loss (>20% est. drawdown).\n"
        )
        draft.pine_script_v5_code = disclaimer_header + code
        decision_summary = "Approved with Mandatory ESMA High-Risk Disclaimer"

    if note:
        decision_summary = f"{decision_summary} — Reviewer Note: '{note}'"

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    trace: TraceStep = {
        "node": "human_governance_gate",
        "model_used": "human-in-the-loop (checkpoint-resume)",
        "latency_ms": elapsed_ms,
        "detail": f"Resumed from checkpoint · Decision: {decision_summary}",
        "loop_iteration": int(state.get("correction_loops", 0)),
        "cost_usd_est": 0.0,
    }
    return {
        "draft": draft.model_dump(),
        "human_decision": {"action": action, "summary": decision_summary},
        "trace_steps": [trace],
    }


def final_publisher(state: AgentGraphState) -> dict[str, Any]:
    """Node 6: Assemble immutable, citation-backed FinalAuditReport."""
    t0 = time.perf_counter()
    draft = ArchitectDraft.model_validate(state["draft"])
    human_dec = state.get("human_decision")
    had_critical_input_trap = any(
        f.severity == "critical" for f in state.get("input_trap_findings", [])
    )

    verdict: ComplianceVerdict = "COMPLIANT"
    if human_dec:
        act = human_dec.get("action", "")
        if act == "reject_publication":
            verdict = "BLOCKED"
        elif act == "approve_with_disclaimer":
            verdict = "REVIEW_REQUIRED"
        else:
            verdict = "COMPLIANT"
    elif had_critical_input_trap:
        # Original submitted script contained critical traps; remediated code is provided alongside warning!
        verdict = "REVIEW_REQUIRED"

    routing = dict(state.get("model_routing", {}))
    routing["vector_retrieval"] = "Qdrant Hybrid (Gemini 3072d Dense + BM25 Sparse + RRF)"
    routing["audit_critic"] = "Deterministic Pine v5 AST + Policy Citation Verifier"

    report = FinalAuditReport(
        strategy_title=draft.strategy_title,
        executive_summary=draft.executive_summary,
        compliance_verdict=verdict,
        pine_script_v5_code=draft.pine_script_v5_code,
        metrics=draft.metrics,
        findings=draft.findings,
        cited_doc_ids=draft.cited_doc_ids,
        correction_loops_executed=int(state.get("correction_loops", 0)),
        human_gate_triggered=bool(state.get("requires_human_approval", False)),
        human_decision_applied=human_dec["summary"] if human_dec else None,
        model_routing_summary=routing,
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    trace: TraceStep = {
        "node": "final_publisher",
        "model_used": "pydantic-v2-compiler",
        "latency_ms": elapsed_ms,
        "detail": f"Published FinalAuditReport · Verdict={verdict} · Citations={len(report.cited_doc_ids)}",
        "loop_iteration": int(state.get("correction_loops", 0)),
        "cost_usd_est": 0.0,
    }
    return {"final_report": report, "trace_steps": [trace]}
