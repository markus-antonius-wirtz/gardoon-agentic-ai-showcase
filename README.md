# Gardoon Ltd. — Enterprise Multi-Agent AI & Hybrid Vector Reference Architecture

[![Live Showcase](https://img.shields.io/badge/Live_Demo-agents.gardoon.ltd-2563eb?style=for-the-badge)](https://agents.gardoon.ltd)
[![Enterprise CI](https://img.shields.io/github/actions/workflow/status/markus-antonius-wirtz/gardoon-agentic-ai-showcase/ci.yml?branch=main&style=for-the-badge&label=CI_Pipeline)](https://github.com/markus-antonius-wirtz/gardoon-agentic-ai-showcase/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12_Strict-10b981?style=for-the-badge)](./backend)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph_%2B_HITL-6366f1?style=for-the-badge)](./backend/app/agents)
[![Qdrant Hybrid](https://img.shields.io/badge/Qdrant-Dense_%2B_BM25_RRF-06b6d4?style=for-the-badge)](./backend/app/knowledge)
[![Kubernetes Helm](https://img.shields.io/badge/Kubernetes-Helm_v2_%2B_HPA-3b82f6?style=for-the-badge)](./deploy/helm/gardoon-agent-showcase)

An open-box ("Glass-Box") enterprise reference system engineered by **[Gardoon Ltd.](https://gardoon.ltd)** as the multi-agent strategy synthesis, anti-repainting code audit, and EU/MiFID risk governance core for **[TradingTackle.ai](https://tradingtackle.ai)**.

Unlike single-prompt chat wrappers that hide backend behavior behind a text box, this platform streams **every LangGraph node transition, parallel Qdrant Hybrid Search score, corrective critic retry, and stateful Human-in-the-Loop (`interrupt`) checkpoint** live into a split-screen engineering console.

---

## Architecture & Multi-Agent Topology

```mermaid
flowchart TD
    Client["Next.js 14 Glass-Box Console (SSE Stream)"] --> API["FastAPI Async Orchestrator"]
    API --> Sup["1. Intake Supervisor (Gemini Flash + Static Pre-Scan)"]
    Sup -->|"LangGraph Send() Parallel Fan-Out"| PineRAG["2a. Pine Script v5 Hybrid RAG (Qdrant)"]
    Sup -->|"LangGraph Send() Parallel Fan-Out"| RiskRAG["2b. Anti-Repainting & MiFID Policy RAG (Qdrant)"]
    PineRAG --> Arch["3. Quant & Pine v5 Architect (Smart Model Routing)"]
    RiskRAG --> Arch
    Arch --> Critic["4. Four-Eyes Audit Critic (AST + Citation Verifier)"]
    Critic -->|"Defects Found (Max 2 Loops -> Escalate to Pro)"| Arch
    Critic -->|"Max Drawdown > 20% or Leverage > 3x (TT-RISK-002)"| HITL["5. Human Governance Gate (LangGraph interrupt + Postgres)"]
    Critic -->|"100% Compliant"| Pub["6. Final Pydantic v2 Audit Publisher"]
    HITL -->|"Command(resume=...) Sign-Off / Auto-Tighten"| Pub
```

---

## Enterprise Capability Matrix

| Capability | Implementation Details |
| :--- | :--- |
| **Python (Master)** | Python 3.12, `uv`, strict `mypy` (`--strict` + Pydantic plugin), `ruff`, async `FastAPI` SSE streaming, deterministic offline-capable `pytest` suite |
| **Multi-Agent AI Systems** | Supervisor decomposition, parallel Map-Reduce (`Send` API), Four-Eyes Evaluator-Optimizer self-correction loop, Smart Model Routing (`Flash` -> `Pro` escalation on retry) |
| **LangChain & LangGraph** | Typed `StateGraph`, `Annotated[..., operator.add]` reducers, `.with_structured_output()`, `AsyncPostgresSaver` checkpointing, stateful `interrupt()` & `Command(resume=...)` |
| **Vector Databases (Advanced)** | **Qdrant** combining **3072-d Dense Semantic Embeddings** + **Sparse BM25 Technical Tokenizer** via **Reciprocal Rank Fusion (`Fusion.RRF`)** and strict `tenant` payload isolation |
| **Cloud, Docker & Kubernetes** | Non-root multi-stage `Dockerfile`s, `docker-compose` + production **Helm v2 Chart** (`Deployment`, `StatefulSet`, `HorizontalPodAutoscaler`, `PodDisruptionBudget`, `NetworkPolicy`, zero-buffering SSE `Ingress`, Downward API pod telemetry) |

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env
# Add your GEMINI_API_KEY to .env (or leave empty to run in deterministic offline demo mode)
docker compose up --build
```

Open `http://localhost:8026` to explore the live Glass-Box Console.

## Local Development & Verification

```bash
# 1. Backend Quality & Tests
cd backend
uv sync
uv run ruff check .
uv run mypy app tests
uv run pytest -v

# 2. Run API locally (port 8000)
uv run uvicorn app.api.main:app --reload --port 8000

# 3. Frontend (port 3000)
cd ../frontend
npm install
npm run dev
```

## Kubernetes Deployment (Helm)

```bash
kubectl create namespace gardoon-ai-prod
kubectl -n gardoon-ai-prod create secret generic gardoon-secrets \
  --from-literal=gemini-api-key="$GEMINI_API_KEY" \
  --from-literal=postgres-password="change-me" \
  --from-literal=postgres-dsn="postgresql://gardoon:change-me@gardoon-postgres:5432/agent_checkpoints"

helm upgrade --install gardoon ./deploy/helm/gardoon-agent-showcase \
  --namespace gardoon-ai-prod
```

---

## About Gardoon Ltd.

Engineered by **[Gardoon Ltd.](https://gardoon.ltd)** — Custom Multi-Agent AI Systems, Hybrid Vector Architectures & Cloud-Native SaaS Engineering.
