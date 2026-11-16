"""FastAPI application with SSE LangGraph streaming, HITL checkpoint resume & K8s telemetry."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import SecretStr

from app.agents.graph import build_agent_graph
from app.agents.static_analyzer import scan_user_submission
from app.api.ratelimit import SlidingWindowRateLimiter
from app.config import get_settings
from app.knowledge.corpus import TRADINGTACKLE_CORPUS
from app.knowledge.scenarios import SHOWCASE_SCENARIOS
from app.knowledge.vector_store import get_knowledge_store
from app.schemas import (
    DocCategory,
    FinalAuditReport,
    HumanInterruptPayload,
    KnowledgeDocument,
    NaiveComparisonResponse,
    ResumeRunRequest,
    RetrievedChunk,
    RunRequest,
    ScenarioPreset,
    SystemTelemetry,
)

logger = logging.getLogger(__name__)
_BOOT_TIME = time.monotonic()


class RuntimeContainer:
    """Holds compiled LangGraph instance, active checkpointer metadata, and rate limiter."""

    def __init__(self) -> None:
        self.graph: Any = None
        self.checkpointer_backend: str = "InMemorySaver"
        self.limiter = SlidingWindowRateLimiter(
            max_requests_per_hour=get_settings().rate_limit_max_requests_per_hour
        )


runtime = RuntimeContainer()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize Qdrant Hybrid Vector DB and PostgreSQL / Memory LangGraph Checkpointer."""
    settings = get_settings()
    store = get_knowledge_store()
    store.ensure_ingested()

    if settings.postgres_dsn:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg_pool import AsyncConnectionPool

            pool: AsyncConnectionPool[Any] = AsyncConnectionPool(
                conninfo=settings.postgres_dsn,
                max_size=10,
                kwargs={"autocommit": True, "prepare_threshold": 0},
                open=False,
            )
            await pool.open()
            pg_saver = AsyncPostgresSaver(pool)
            await pg_saver.setup()
            runtime.graph = build_agent_graph(checkpointer=pg_saver)
            runtime.checkpointer_backend = "AsyncPostgresSaver (PostgreSQL 16)"
            logger.info("Initialized LangGraph with AsyncPostgresSaver.")
            try:
                yield
            finally:
                await pool.close()
            return
        except Exception as exc:
            logger.warning("PostgreSQL checkpointer unavailable (%s); falling back to InMemorySaver.", exc)

    runtime.graph = build_agent_graph(checkpointer=InMemorySaver())
    runtime.checkpointer_backend = "InMemorySaver (Stateful RAM)"
    yield


app = FastAPI(
    title="Gardoon Ltd. — Enterprise Multi-Agent Quant & Compliance API",
    version="1.0.0",
    description=(
        "Production Multi-Agent LangGraph + Qdrant Hybrid Search showcase engineered by Gardoon Ltd. "
        "for TradingTackle.ai."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse_frame(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _ensure_graph() -> Any:
    if runtime.graph is None:
        runtime.graph = build_agent_graph(checkpointer=InMemorySaver())
    return runtime.graph


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Kubernetes liveness & readiness probe endpoint."""
    return {"status": "ok", "service": "gardoon-agentic-showcase"}


@app.get("/api/system/telemetry", response_model=SystemTelemetry)
async def system_telemetry() -> SystemTelemetry:
    """Expose live container, Kubernetes pod, Qdrant Hybrid DB, and checkpointer telemetry."""
    settings = get_settings()
    store = get_knowledge_store()
    if store.indexed_count == 0:
        store.ensure_ingested()
    return SystemTelemetry(
        status="healthy",
        pod_name=settings.k8s_pod_name,
        namespace=settings.k8s_namespace,
        node_name=settings.k8s_node_name,
        cluster_topology=settings.cluster_topology,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        qdrant_mode=store.qdrant_mode,
        qdrant_collection=store.collection_name,
        indexed_documents=store.indexed_count,
        vector_dimensions=store.vector_dim,
        hybrid_fusion="Dense Cosine + Sparse BM25 -> Reciprocal Rank Fusion (RRF)",
        checkpointer_backend=runtime.checkpointer_backend,
        uptime_seconds=int(time.monotonic() - _BOOT_TIME),
        models_configured={
            "supervisor_triage": settings.gemini_fast_model,
            "architect_balanced": settings.gemini_fast_model,
            "architect_deep_escalation": settings.gemini_reasoning_model,
            "dense_embeddings": settings.gemini_embedding_model,
        },
        rate_limit_per_hour=settings.rate_limit_max_requests_per_hour,
    )


@app.get("/api/scenarios", response_model=list[ScenarioPreset])
async def list_scenarios() -> list[ScenarioPreset]:
    """Return curated 1-click scenarios for immediate evaluation."""
    return SHOWCASE_SCENARIOS


@app.get("/api/knowledge/documents", response_model=list[KnowledgeDocument])
async def list_corpus_documents(
    tenant: Annotated[str, Query()] = "tradingtackle",
    category: Annotated[DocCategory | None, Query()] = None,
) -> list[KnowledgeDocument]:
    """Browse indexed knowledge base documents with multi-tenant filtering."""
    docs = [d for d in TRADINGTACKLE_CORPUS if d.tenant == tenant]
    if category is not None:
        docs = [d for d in docs if d.category == category]
    return docs


@app.get("/api/knowledge/search", response_model=list[RetrievedChunk])
async def search_knowledge(
    q: Annotated[str, Query(min_length=2, max_length=300)],
    tenant: Annotated[str, Query()] = "tradingtackle",
    category: Annotated[DocCategory | None, Query()] = None,
    top_k: Annotated[int, Query(ge=1, le=15)] = 6,
) -> list[RetrievedChunk]:
    """Interactive Qdrant Hybrid Search endpoint for the Vector DB Inspector UI."""
    store = get_knowledge_store()
    return store.hybrid_search(q, tenant=tenant, category=category, top_k=top_k)


async def _stream_graph_execution(
    graph_input: Any,
    thread_id: str,
    tenant: str,
    remaining_quota: int,
) -> AsyncIterator[str]:
    """Stream real-time LangGraph state updates, Qdrant chunks, HITL interrupts & final reports."""
    graph = _ensure_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    t_start = time.perf_counter()
    total_cost = 0.0

    yield _sse_frame(
        "run_started",
        {
            "thread_id": thread_id,
            "tenant": tenant,
            "remaining_hourly_quota": remaining_quota,
        },
    )

    try:
        async for update in graph.astream(graph_input, config=config, stream_mode="updates"):
            if not isinstance(update, dict):
                continue

            for node_name, node_payload in update.items():
                if node_name == "__interrupt__":
                    interrupt_items = node_payload if isinstance(node_payload, (list, tuple)) else [node_payload]
                    raw_val = getattr(interrupt_items[0], "value", interrupt_items[0])
                    if isinstance(raw_val, dict):
                        payload = HumanInterruptPayload(thread_id=thread_id, **raw_val)
                        yield _sse_frame("hitl_interrupt", payload.model_dump())
                    continue

                if not isinstance(node_payload, dict):
                    continue

                steps = node_payload.get("trace_steps", [])
                latest_step = steps[-1] if steps else None
                if latest_step:
                    total_cost += float(latest_step.get("cost_usd_est", 0.0))

                chunks = node_payload.get("retrieved_chunks")
                serialized_chunks = (
                    [c.model_dump() if hasattr(c, "model_dump") else c for c in chunks]
                    if chunks
                    else None
                )

                yield _sse_frame(
                    "node_completed",
                    {
                        "node": node_name,
                        "trace": latest_step,
                        "retrieved_chunks": serialized_chunks,
                        "critic_issues": node_payload.get("critic_issues"),
                        "correction_loops": node_payload.get("correction_loops"),
                    },
                )

                final_rep = node_payload.get("final_report")
                if final_rep is not None:
                    rep_dict = (
                        final_rep.model_dump()
                        if isinstance(final_rep, FinalAuditReport)
                        else final_rep
                    )
                    total_ms = int((time.perf_counter() - t_start) * 1000)
                    yield _sse_frame(
                        "final_report",
                        {
                            "thread_id": thread_id,
                            "total_latency_ms": total_ms,
                            "total_cost_usd_est": round(total_cost, 5),
                            "report": rep_dict,
                        },
                    )
    except Exception as exc:
        logger.exception("Error during LangGraph streaming execution")
        yield _sse_frame("run_error", {"message": str(exc)})


@app.post("/api/runs/stream")
async def start_streaming_run(req: RunRequest, request: Request) -> StreamingResponse:
    """Start a new stateful Multi-Agent LangGraph run and stream events via SSE."""
    settings = get_settings()
    if len(req.prompt) > settings.max_input_chars:
        raise HTTPException(status_code=400, detail="Input exceeds maximum character limit.")

    remaining = runtime.limiter.check_or_raise(request)
    thread_id = f"gd-{uuid.uuid4().hex[:12]}"
    initial_state: dict[str, Any] = {
        "prompt": req.prompt,
        "tenant": req.tenant,
        "reasoning_tier": req.reasoning_tier,
        "retrieved_chunks": [],
        "trace_steps": [],
    }
    return StreamingResponse(
        _stream_graph_execution(initial_state, thread_id, req.tenant, remaining),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/runs/{thread_id}/resume")
async def resume_interrupted_run(
    thread_id: str,
    req: ResumeRunRequest,
    request: Request,
) -> StreamingResponse:
    """Resume a paused Human-in-the-Loop LangGraph checkpoint via Command(resume=...)."""
    remaining = runtime.limiter.check_or_raise(request)
    resume_cmd: Any = Command(
        resume={"action": req.action, "reviewer_note": req.reviewer_note}
    )
    return StreamingResponse(
        _stream_graph_execution(resume_cmd, thread_id, "tradingtackle", remaining),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/runs/compare-naive", response_model=NaiveComparisonResponse)
async def compare_with_naive_single_llm(
    req: RunRequest,
    request: Request,
) -> NaiveComparisonResponse:
    """Demonstrate why a single ungrounded LLM prompt fails enterprise compliance vs Multi-Agent."""
    runtime.limiter.check_or_raise(request)
    t0 = time.perf_counter()
    settings = get_settings()
    traps, lev_x, hinted_dd = scan_user_submission(req.prompt)

    naive_text = ""
    model_label = settings.gemini_fast_model
    if settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key-here":
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_fast_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0.4,
                timeout=25,
            )
            msg = llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "Briefly summarize or lightly clean up the user's trading idea in 6-8 lines "
                            "like a generic general-purpose assistant without access to private company rules."
                        )
                    ),
                    HumanMessage(content=req.prompt),
                ]
            )
            naive_text = str(msg.content)
        except Exception as exc:
            logger.warning("Naive comparison fallback: %s", exc)

    if not naive_text:
        naive_text = (
            "Here is a quick summary of your strategy idea: It uses a daily price filter with an EMA crossover "
            "to enter momentum trends. Make sure to test it on historical charts and manage your risk carefully!"
        )
        model_label = "single-shot-ungrounded-llm"

    missed: list[str] = [
        "Zero access to private Qdrant knowledge base (`TT-PINE-*`, `TT-REP-*`, `TT-RISK-*` policy IDs unknown).",
        "No deterministic Four-Eyes Critic loop verifying `commission_value=0.06`, `slippage=2`, and `strategy.exit(stop=...)`.",
    ]
    for f in traps:
        missed.append(f"Missed mandatory enterprise enforcement for [{f.rule_id}]: {f.title}")
    if lev_x > 3.0 or hinted_dd > 20.0:
        missed.append(
            "Cannot pause workflow via stateful checkpoint `interrupt()` for mandatory Human Risk Officer sign-off (>20% DD)."
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return NaiveComparisonResponse(
        naive_model=f"{model_label} (Single Prompt · No RAG · No Critic · No HITL)",
        naive_output=naive_text,
        missed_risks=missed,
        latency_ms=elapsed_ms,
        why_multi_agent_wins=[
            "Hybrid Vector Grounding: Combines 3072-d semantic embeddings + BM25 code-token matching in Qdrant.",
            "Four-Eyes Self-Correction: Independent Critic rejects uncompilable Pine v4 or zero-fee backtests automatically.",
            "Stateful Governance: Suspends high-risk runs (>20% Drawdown) in PostgreSQL checkpoints until human sign-off.",
            "Auditability (EU AI Act): Produces immutable rule-ID citations and cost/latency telemetry per graph node.",
        ],
    )
