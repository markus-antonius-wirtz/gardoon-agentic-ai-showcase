"""Comprehensive enterprise test suite: Hybrid Qdrant RAG, Multi-Tenancy, LangGraph & HITL."""

from __future__ import annotations

import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents.graph import build_agent_graph
from app.agents.static_analyzer import scan_user_submission, verify_generated_pine_v5
from app.api.main import app
from app.config import Settings
from app.knowledge.scenarios import SHOWCASE_SCENARIOS
from app.knowledge.vector_store import HybridKnowledgeStore


@pytest.fixture
def isolated_store() -> HybridKnowledgeStore:
    """Create an isolated in-memory Qdrant Hybrid store in deterministic offline mode."""
    test_settings = Settings(
        GEMINI_API_KEY="",
        QDRANT_URL="",
        QDRANT_COLLECTION="test_enterprise_kb",
    )
    store = HybridKnowledgeStore(settings=test_settings)
    store.ensure_ingested()
    return store


def test_qdrant_hybrid_rrf_retrieves_exact_repainting_rule(
    isolated_store: HybridKnowledgeStore,
) -> None:
    results = isolated_store.hybrid_search(
        "request.security barmerge.lookahead_on intraday future leak",
        tenant="tradingtackle",
        category="anti_repainting_audit",
        top_k=4,
    )
    assert len(results) >= 1
    doc_ids = [r.doc_id for r in results]
    assert "TT-REP-001" in doc_ids
    top = results[0]
    assert 0.0 <= top.dense_score <= 1.0
    assert 0.0 <= top.sparse_score <= 1.0
    assert top.rrf_score == 1.0


def test_qdrant_strict_multi_tenant_isolation(isolated_store: HybridKnowledgeStore) -> None:
    tt_hits = isolated_store.hybrid_search(
        "Kubernetes PodDisruptionBudget HPA GD-OPS-001",
        tenant="tradingtackle",
        top_k=10,
    )
    assert all(hit.tenant == "tradingtackle" for hit in tt_hits)
    assert all(not hit.doc_id.startswith("GD-OPS-") for hit in tt_hits)

    gd_hits = isolated_store.hybrid_search(
        "Kubernetes PodDisruptionBudget HPA GD-OPS-001",
        tenant="gardoon_cloud",
        top_k=5,
    )
    assert len(gd_hits) == 2
    assert all(hit.tenant == "gardoon_cloud" for hit in gd_hits)
    assert "GD-OPS-001" in [h.doc_id for h in gd_hits]


def test_static_analyzer_catches_submission_traps_and_validates_v5() -> None:
    scenario_2_prompt = SHOWCASE_SCENARIOS[1].prompt
    findings, _, _ = scan_user_submission(scenario_2_prompt)
    rule_ids = {f.rule_id for f in findings}
    assert {"TT-REP-001", "TT-PINE-001", "TT-REP-005", "TT-REP-003", "TT-RISK-001"}.issubset(
        rule_ids
    )

    bad_defects = verify_generated_pine_v5(
        "//@version=4\nstudy('Bad')\n", "Guaranteed 98% winrate!"
    )
    assert len(bad_defects) >= 4


def test_langgraph_parallel_fanout_and_human_interrupt_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    graph = build_agent_graph(checkpointer=InMemorySaver())

    # 1. Scenario 1: Clean autonomous run without interrupt
    cfg_clean: dict[str, Any] = {"configurable": {"thread_id": "test-clean-01"}}
    clean_out = graph.invoke(
        {
            "prompt": SHOWCASE_SCENARIOS[0].prompt,
            "tenant": "tradingtackle",
            "reasoning_tier": "balanced",
            "retrieved_chunks": [],
            "trace_steps": [],
        },
        config=cfg_clean,
    )
    assert clean_out["final_report"] is not None
    assert clean_out["final_report"].compliance_verdict == "COMPLIANT"
    assert len(clean_out["retrieved_chunks"]) >= 6

    # 2. Scenario 3: High-drawdown run -> pauses at human_governance_gate via interrupt()
    cfg_hitl: dict[str, Any] = {"configurable": {"thread_id": "test-hitl-03"}}
    paused_out = graph.invoke(
        {
            "prompt": SHOWCASE_SCENARIOS[2].prompt,
            "tenant": "tradingtackle",
            "reasoning_tier": "balanced",
            "retrieved_chunks": [],
            "trace_steps": [],
        },
        config=cfg_hitl,
    )
    assert "__interrupt__" in paused_out or paused_out.get("final_report") is None
    snapshot = graph.get_state(cfg_hitl)
    assert "human_governance_gate" in snapshot.next

    # 3. Resume from checkpoint with Risk Officer Auto-Tighten action
    resumed_out = graph.invoke(
        Command(
            resume={
                "action": "tighten_risk_parameters",
                "reviewer_note": "Enforce retail 15% cap",
            }
        ),
        config=cfg_hitl,
    )
    final_report = resumed_out["final_report"]
    assert final_report is not None
    assert final_report.human_gate_triggered is True
    assert final_report.compliance_verdict == "COMPLIANT"
    assert final_report.metrics.max_drawdown_est_pct < 20.0
    assert "strategy.risk.max_drawdown" in final_report.pine_script_v5_code


@pytest.mark.asyncio
async def test_fastapi_sse_streaming_and_telemetry_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/api/health")
        assert health.status_code == 200

        telemetry = await client.get("/api/system/telemetry")
        assert telemetry.status_code == 200
        tel_data = telemetry.json()
        assert tel_data["indexed_documents"] >= 40
        assert "RRF" in tel_data["hybrid_fusion"]

        # Stream Scenario 3 and verify hitl_interrupt SSE frame arrives, then resume!
        stream_res = await client.post(
            "/api/runs/stream",
            json={
                "prompt": SHOWCASE_SCENARIOS[2].prompt,
                "tenant": "tradingtackle",
                "reasoning_tier": "balanced",
            },
        )
        assert stream_res.status_code == 200
        body_text = stream_res.text
        assert "event: run_started" in body_text
        assert "event: node_completed" in body_text
        assert "event: hitl_interrupt" in body_text

        # Extract thread_id from run_started frame
        first_data_line = next(
            line for line in body_text.splitlines() if line.startswith("data: ")
        )
        thread_id = json.loads(first_data_line.removeprefix("data: "))["thread_id"]

        resume_res = await client.post(
            f"/api/runs/{thread_id}/resume",
            json={"action": "approve_with_disclaimer", "reviewer_note": "Approved for pro tier"},
        )
        assert resume_res.status_code == 200
        assert "event: final_report" in resume_res.text
        assert "REVIEW_REQUIRED" in resume_res.text
