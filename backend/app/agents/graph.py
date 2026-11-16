"""LangGraph StateGraph assembly with AsyncPostgresSaver / InMemorySaver checkpointing."""

from __future__ import annotations

import logging
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    audit_critic,
    dispatch_parallel_retrievers,
    final_publisher,
    human_governance_gate,
    intake_supervisor,
    quant_architect,
    retrieve_pine_docs,
    retrieve_risk_policies,
    route_after_critic,
)
from app.agents.state import AgentGraphState

logger = logging.getLogger(__name__)


def build_agent_graph(checkpointer: BaseCheckpointSaver[Any] | None = None) -> Any:
    """Compile the Multi-Agent Quant & Compliance StateGraph."""
    builder = StateGraph(AgentGraphState)

    builder.add_node("intake_supervisor", intake_supervisor)
    builder.add_node("retrieve_pine_docs", cast(Any, retrieve_pine_docs))
    builder.add_node("retrieve_risk_policies", cast(Any, retrieve_risk_policies))
    builder.add_node("quant_architect", quant_architect)
    builder.add_node("audit_critic", audit_critic)
    builder.add_node("human_governance_gate", human_governance_gate)
    builder.add_node("final_publisher", final_publisher)

    # 1. Start -> Intake Supervisor
    builder.add_edge(START, "intake_supervisor")

    # 2. Parallel Fan-Out via Send() -> Qdrant Pine v5 Docs + Qdrant Risk/Repainting Docs
    builder.add_conditional_edges(
        "intake_supervisor",
        dispatch_parallel_retrievers,
        ["retrieve_pine_docs", "retrieve_risk_policies"],
    )

    # 3. Fan-In Join -> Quant Architect
    builder.add_edge("retrieve_pine_docs", "quant_architect")
    builder.add_edge("retrieve_risk_policies", "quant_architect")

    # 4. Quant Architect -> Four-Eyes Audit Critic
    builder.add_edge("quant_architect", "audit_critic")

    # 5. Conditional Corrective Loop / HITL Gate / Direct Publish
    builder.add_conditional_edges(
        "audit_critic",
        route_after_critic,
        {
            "quant_architect": "quant_architect",
            "human_governance_gate": "human_governance_gate",
            "final_publisher": "final_publisher",
        },
    )

    # 6. Human Governance Gate -> Final Publisher -> END
    builder.add_edge("human_governance_gate", "final_publisher")
    builder.add_edge("final_publisher", END)

    active_saver = checkpointer if checkpointer is not None else InMemorySaver()
    return builder.compile(checkpointer=active_saver)
