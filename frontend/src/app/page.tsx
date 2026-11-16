'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  Cpu,
  Database,
  ExternalLink,
  GitCompare,
  Layers,
  Play,
  ShieldAlert,
  Sparkles,
  Terminal,
} from 'lucide-react';
import { GraphVisualizer } from '@/components/GraphVisualizer';
import { KubernetesBlueprint } from '@/components/KubernetesBlueprint';
import { VectorInspector } from '@/components/VectorInspector';
import {
  FinalAuditReport,
  HumanActionChoice,
  HumanInterruptPayload,
  NaiveComparisonResponse,
  RetrievedChunk,
  ScenarioPreset,
  SystemTelemetry,
  TraceStep,
} from '@/types/showcase';

const DEFAULT_SCENARIOS: ScenarioPreset[] = [
  {
    id: 'volatility-atr-breakout',
    badge: 'Scenario 01 · Clean Build + Self-Check',
    title: 'Adaptive Volatility Breakout (EMA 200 + ATR Trailing Stop)',
    subtitle:
      'Synthesizes production Pine Script v5 with hybrid documentation grounding and passes Critic verification.',
    highlight_feature: 'Parallel Hybrid RAG + Pine v5 Synthesis',
    prompt:
      'Design a production-ready Pine Script v5 trend-following breakout strategy for BTCUSDT and EURUSD on the 1H timeframe. Use a 200-EMA regime filter, Donchian/20-bar high breakout entries with volume confirmation, and a dynamic 2.2x ATR(14) stop-loss and trailing exit via strategy.exit(). Ensure realistic friction (commission & slippage) and compliant position sizing.',
    tenant: 'tradingtackle',
  },
  {
    id: 'repainting-trap-audit',
    badge: 'Scenario 02 · Repainting & YMYL Trap',
    title: "Audit Submitted '96% Winrate' Multi-Timeframe Script",
    subtitle:
      'Exposes hidden future-leak (`lookahead_on`) and zero-fee illusions that naive single-LLM chats miss, then auto-remediates.',
    highlight_feature: 'Corrective Self-Reflection Loop (Critic -> Architect)',
    prompt:
      "Audit and remediate our draft strategy that achieved a 96% guaranteed winrate on 15m charts:\n//@version=4\nstudy('Guaranteed 96% Alpha Sniper', overlay=true)\ndailyClose = security(syminfo.tickerid, 'D', close, lookahead=barmerge.lookahead_on)\nfast = ema(close, 9)\nif close > dailyClose and fast > fast[1]\n    // Enter 100% equity with zero commission on Heikin-Ashi candles, no stop-loss needed!",
    tenant: 'tradingtackle',
  },
  {
    id: 'high-drawdown-hitl',
    badge: 'Scenario 03 · Human-in-the-Loop Gate',
    title: 'Aggressive 5x Leveraged Momentum Swing (Drawdown > 20%)',
    subtitle:
      'Triggers Policy TT-RISK-002 (>20% Max Drawdown / >3x Leverage) and pauses LangGraph via interrupt() for human governance.',
    highlight_feature: 'Stateful LangGraph interrupt() & Checkpoint Resume',
    prompt:
      'Build an aggressive high-beta crypto momentum strategy for SOLUSDT 4H using 5x perpetual futures leverage and 45% equity allocation per trade, riding MACD + Supertrend breakouts with wide 4.5x ATR stops (expected max drawdown around 28% - 32% during choppy regimes).',
    tenant: 'tradingtackle',
  },
];

type InspectorTab = 'graph' | 'vector' | 'k8s';

export default function ShowcasePage() {
  const [scenarios, setScenarios] = useState<ScenarioPreset[]>(DEFAULT_SCENARIOS);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(
    DEFAULT_SCENARIOS[1].id
  );
  const [prompt, setPrompt] = useState<string>(DEFAULT_SCENARIOS[1].prompt);
  const [reasoningTier, setReasoningTier] = useState<'balanced' | 'deep'>(
    'balanced'
  );

  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('graph');
  const [highlightedDocId, setHighlightedDocId] = useState<string | null>(null);

  // Live streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [traces, setTraces] = useState<TraceStep[]>([]);
  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [correctionLoops, setCorrectionLoops] = useState(0);
  const [hitlInterrupt, setHitlInterrupt] =
    useState<HumanInterruptPayload | null>(null);
  const [reviewerNote, setReviewerNote] = useState('');
  const [finalReport, setFinalReport] = useState<FinalAuditReport | null>(null);
  const [totalLatencyMs, setTotalLatencyMs] = useState<number | null>(null);
  const [totalCostUsd, setTotalCostUsd] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Naive single-LLM comparison state
  const [comparingNaive, setComparingNaive] = useState(false);
  const [naiveComparison, setNaiveComparison] =
    useState<NaiveComparisonResponse | null>(null);

  useEffect(() => {
    fetch('/api/scenarios')
      .then((r) => (r.ok ? r.json() : null))
      .then((data: ScenarioPreset[] | null) => {
        if (data && data.length > 0) setScenarios(data);
      })
      .catch(() => {});

    fetch('/api/system/telemetry')
      .then((r) => (r.ok ? r.json() : null))
      .then((data: SystemTelemetry | null) => {
        if (data) setTelemetry(data);
      })
      .catch(() => {});
  }, []);

  const handleSelectScenario = (sc: ScenarioPreset) => {
    setSelectedScenarioId(sc.id);
    setPrompt(sc.prompt);
    setErrorMessage(null);
    setNaiveComparison(null);
  };

  const predictNextActiveNodes = (justCompleted: string): string[] => {
    switch (justCompleted) {
      case 'intake_supervisor':
        return ['retrieve_pine_docs', 'retrieve_risk_policies'];
      case 'retrieve_pine_docs':
      case 'retrieve_risk_policies':
        return ['quant_architect'];
      case 'quant_architect':
        return ['audit_critic'];
      case 'audit_critic':
      case 'human_governance_gate':
        return ['final_publisher'];
      default:
        return [];
    }
  };

  const consumeSseStream = async (res: Response) => {
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('Streaming body unavailable.');

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split('\n\n');
      buffer = frames.pop() || '';

      for (const rawFrame of frames) {
        const lines = rawFrame.split('\n');
        let eventType = 'message';
        let dataStr = '';
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataStr += line.slice(5).trim();
          }
        }
        if (!dataStr) continue;

        const payload = JSON.parse(dataStr);

        if (eventType === 'node_completed') {
          const nodeName: string = payload.node;
          setCompletedNodes((prev) =>
            prev.includes(nodeName) ? prev : [...prev, nodeName]
          );
          setActiveNodes(predictNextActiveNodes(nodeName));

          if (payload.trace) {
            const step: TraceStep = payload.trace;
            setTraces((prev) => {
              const next = [...prev, step];
              const sumLatency = next.reduce((acc, s) => acc + (s.latency_ms || 0), 0);
              setTotalLatencyMs(sumLatency);
              return next;
            });
            setTotalCostUsd((prev) => prev + (step.cost_usd_est || 0));
          }

          if (typeof payload.correction_loops === 'number') {
            setCorrectionLoops(payload.correction_loops);
            if (
              Array.isArray(payload.critic_issues) &&
              payload.critic_issues.length > 0
            ) {
              setActiveNodes(['quant_architect']);
            }
          }

          if (Array.isArray(payload.retrieved_chunks)) {
            setRetrievedChunks((prev) => {
              const map = new Map(prev.map((c) => [c.doc_id, c]));
              for (const ch of payload.retrieved_chunks as RetrievedChunk[]) {
                map.set(ch.doc_id, ch);
              }
              return Array.from(map.values());
            });
          }
        } else if (eventType === 'hitl_interrupt') {
          setActiveNodes([]);
          setHitlInterrupt(payload as HumanInterruptPayload);
        } else if (eventType === 'final_report') {
          setActiveNodes([]);
          setHitlInterrupt(null);
          setFinalReport(payload.report as FinalAuditReport);
          if (typeof payload.total_latency_ms === 'number') {
            setTotalLatencyMs((prev) => (prev ?? 0) + payload.total_latency_ms);
          }
        } else if (eventType === 'run_error') {
          setActiveNodes([]);
          setErrorMessage(payload.message || 'Pipeline execution failed.');
        }
      }
    }
  };

  const handleRunPipeline = async () => {
    if (!prompt.trim() || isStreaming) return;
    setIsStreaming(true);
    setErrorMessage(null);
    setFinalReport(null);
    setHitlInterrupt(null);
    setTraces([]);
    setRetrievedChunks([]);
    setCompletedNodes([]);
    setCorrectionLoops(0);
    setTotalLatencyMs(null);
    setTotalCostUsd(0);
    setInspectorTab('graph');
    setActiveNodes(['intake_supervisor']);

    try {
      const res = await fetch('/api/runs/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          scenario_id: selectedScenarioId,
          tenant: 'tradingtackle',
          reasoning_tier: reasoningTier,
        }),
      });
      await consumeSseStream(res);
    } catch (err: unknown) {
      setActiveNodes([]);
      setErrorMessage(
        err instanceof Error ? err.message : 'Unexpected streaming error.'
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleResumeHitl = async (action: HumanActionChoice) => {
    if (!hitlInterrupt || isStreaming) return;
    const threadId = hitlInterrupt.thread_id;
    setIsStreaming(true);
    setErrorMessage(null);
    setActiveNodes(['human_governance_gate']);

    try {
      const res = await fetch(`/api/runs/${threadId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          reviewer_note: reviewerNote.trim(),
        }),
      });
      await consumeSseStream(res);
      setReviewerNote('');
    } catch (err: unknown) {
      setActiveNodes([]);
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to resume checkpoint.'
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleCompareNaive = async () => {
    if (!prompt.trim() || comparingNaive) return;
    setComparingNaive(true);
    try {
      const res = await fetch('/api/runs/compare-naive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          tenant: 'tradingtackle',
          reasoning_tier: 'balanced',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data: NaiveComparisonResponse = await res.json();
      setNaiveComparison(data);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Comparison request failed.'
      );
    } finally {
      setComparingNaive(false);
    }
  };

  const jumpToCitation = (docId: string) => {
    setHighlightedDocId(docId);
    setInspectorTab('vector');
  };

  const copyPineCode = () => {
    if (!finalReport) return;
    navigator.clipboard.writeText(finalReport.pine_script_v5_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const verdictBadge = (verdict: FinalAuditReport['compliance_verdict']) => {
    if (verdict === 'COMPLIANT') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 border border-emerald-400/40 text-emerald-300">
          <CheckCircle2 className="w-4 h-4" /> COMPLIANT · VERIFIED PINE v5
        </span>
      );
    }
    if (verdict === 'REVIEW_REQUIRED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 border border-amber-400/40 text-amber-300">
          <AlertTriangle className="w-4 h-4" /> REMEDIATED / ESMA RISK DISCLOSURE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/15 border border-red-400/40 text-red-300">
        <AlertOctagon className="w-4 h-4" /> BLOCKED BY RISK GOVERNANCE
      </span>
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Executive Top Navigation */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-surface-base/85 border-b border-slate-800/80">
        <div className="max-w-[1480px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <a
              href="https://gardoon.ltd"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2.5 group"
            >
              <img
                src="/favicon.svg"
                alt="Gardoon Ltd."
                className="w-8 h-8 shrink-0"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-extrabold tracking-tight text-white text-sm sm:text-base group-hover:text-brand-400 transition">
                    GARDOON LTD.
                  </span>
                  <span className="hidden md:inline-block text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded bg-brand-500/15 border border-brand-500/30 text-brand-300">
                    Multi-Agent AI Lab
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  Enterprise LangGraph, Hybrid Vector DB & Cloud Reference Architecture
                </p>
              </div>
            </a>
          </div>

          <div className="flex items-center gap-2.5">
            {telemetry && (
              <button
                type="button"
                onClick={() => setInspectorTab('k8s')}
                className="hidden lg:inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 hover:border-emerald-500/40 text-xs font-mono text-slate-300 transition"
              >
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Pod: {telemetry.pod_name}</span>
                <span className="text-slate-600">|</span>
                <span className="text-cyan-300">
                  Qdrant {telemetry.indexed_documents} docs
                </span>
              </button>
            )}

            <a
              href="https://github.com/markus-antonius-wirtz/gardoon-agentic-ai-showcase"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition"
            >
              <Code2 className="w-3.5 h-3.5 text-emerald-400" />
              GitHub &amp; K8s Helm
            </a>

            <a
              href="https://tradingtackle.ai"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition"
            >
              Case Study: TradingTackle.ai
              <ExternalLink className="w-3.5 h-3.5 text-brand-400" />
            </a>

            <a
              href="https://gardoon.ltd"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white shadow-glow-sm transition"
            >
              Gardoon.ltd
              <ArrowUpRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Capability Verification Strip */}
        <div className="border-t border-slate-800/60 bg-surface-subtle/70">
          <div className="max-w-[1480px] mx-auto px-4 sm:px-6 py-2 flex items-center gap-2 overflow-x-auto text-[11px] font-mono text-slate-300">
            <span className="text-slate-500 uppercase tracking-wider shrink-0">
              Verified Stack:
            </span>
            {[
              'Python 3.12 (mypy --strict)',
              'Multi-Agent Orchestration',
              'LangGraph StateGraph + Send() + interrupt()',
              'LangChain Structured IO',
              'Qdrant Hybrid DB (Dense 3072d + BM25 RRF)',
              'PostgreSQL Checkpointing',
              'Docker & Kubernetes Helm',
            ].map((badge) => (
              <span
                key={badge}
                className="px-2.5 py-0.5 rounded-md bg-slate-900/90 border border-slate-800 text-slate-300 shrink-0"
              >
                {badge}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Main Split-Screen Glass-Box Console */}
      <main className="flex-1 max-w-[1480px] w-full mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN (7 cols): Business Case Study, Scenarios, HITL Governance & Output */}
        <div className="lg:col-span-7 space-y-5">
          {/* Hero Case Study Card */}
          <section className="rounded-2xl bg-gradient-to-br from-surface-elevated via-surface-subtle to-surface-base border border-slate-800/90 p-5 shadow-exec">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                Live Production Architecture · Glass-Box Interactive Demo
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Engineered by Gardoon Ltd.
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Autonomous Quant Strategy, Anti-Repainting & MiFID Compliance Studio
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1.5 leading-relaxed">
              Built as the multi-agent verification core for{' '}
              <a
                href="https://tradingtackle.ai"
                target="_blank"
                rel="noreferrer"
                className="text-brand-400 hover:underline font-medium"
              >
                TradingTackle.ai
              </a>
              . Unlike single-prompt chatbots, this pipeline dispatches parallel{' '}
              <strong className="text-white">Qdrant Hybrid Vector</strong> retrievers,
              enforces deterministic <strong className="text-white">Four-Eyes Critic</strong>{' '}
              loops, and suspends high-risk strategies via{' '}
              <strong className="text-white">LangGraph Human-in-the-Loop</strong>{' '}
              checkpoints.
            </p>

            {/* 3 One-Click Scenario Cards */}
            <div className="mt-4">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                1-Click Interactive Evaluation Scenarios
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                {scenarios.map((sc) => {
                  const selected = sc.id === selectedScenarioId;
                  return (
                    <button
                      key={sc.id}
                      type="button"
                      onClick={() => handleSelectScenario(sc)}
                      className={`text-left rounded-xl border p-3 transition-all flex flex-col justify-between ${
                        selected
                          ? 'border-brand-500 bg-brand-950/30 shadow-glow-sm'
                          : 'border-slate-800/90 bg-surface-subtle/80 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="text-[10px] font-mono text-brand-400 font-semibold">
                          {sc.badge}
                        </div>
                        <div className="text-xs font-bold text-white mt-1 line-clamp-2">
                          {sc.title}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-3 leading-snug">
                          {sc.subtitle}
                        </p>
                      </div>
                      <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-[10px] font-mono text-emerald-400 truncate">
                        ✦ {sc.highlight_feature}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Prompt Input + Controls */}
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <label
                  htmlFor="strategy-prompt"
                  className="font-semibold text-slate-200 flex items-center gap-1.5"
                >
                  <Terminal className="w-3.5 h-3.5 text-brand-400" /> Strategy
                  Mandate or Submitted Pine Script
                </label>
                <div className="flex items-center gap-1.5 font-mono text-[11px]">
                  <span className="text-slate-400">Model Routing:</span>
                  <select
                    value={reasoningTier}
                    onChange={(e) =>
                      setReasoningTier(e.target.value as 'balanced' | 'deep')
                    }
                    className="bg-slate-900 border border-slate-700 rounded-md px-2 py-0.5 text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    <option value="balanced">
                      Smart Tier (Flash + Auto-Escalate)
                    </option>
                    <option value="deep">Deep Tier (Gemini 2.5 Pro)</option>
                  </select>
                </div>
              </div>

              <textarea
                id="strategy-prompt"
                rows={5}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full rounded-xl bg-slate-950/90 border border-slate-800 focus:border-brand-500 focus:outline-none p-3.5 text-xs sm:text-sm font-mono text-slate-100 leading-relaxed"
                placeholder="Describe a trading strategy or paste a Pine Script draft to audit..."
              />

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2.5">
                  <button
                    type="button"
                    onClick={handleRunPipeline}
                    disabled={isStreaming || !prompt.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-xs sm:text-sm font-bold text-white shadow-glow-md transition"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    {isStreaming
                      ? 'Executing Multi-Agent Graph…'
                      : 'Run Multi-Agent Pipeline'}
                  </button>

                  <button
                    type="button"
                    onClick={handleCompareNaive}
                    disabled={comparingNaive || !prompt.trim()}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200 transition disabled:opacity-50"
                  >
                    <GitCompare className="w-4 h-4 text-cyan-400" />
                    {comparingNaive
                      ? 'Comparing…'
                      : 'Why Not Just Ask Standard Chat?'}
                  </button>
                </div>

                <span className="text-[11px] font-mono text-slate-400">
                  Watch live state transitions on the right →
                </span>
              </div>
            </div>
          </section>

          {/* Error Banner */}
          {errorMessage && (
            <div className="rounded-xl bg-red-950/40 border border-red-500/50 p-4 text-xs text-red-200 font-mono">
              ⚠ {errorMessage}
            </div>
          )}

          {/* HUMAN-IN-THE-LOOP GOVERNANCE GATE (interrupt() card!) */}
          {hitlInterrupt && (
            <section className="rounded-2xl bg-amber-950/20 border-2 border-amber-500/70 p-5 shadow-glow-amber space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-500/20 border border-amber-400/50 text-amber-300">
                  <ShieldAlert className="w-4 h-4 animate-pulse" />
                  LangGraph interrupt() · Human Risk Officer Gate Active
                </span>
                <span className="text-xs font-mono text-amber-200/80">
                  Thread Checkpoint: {hitlInterrupt.thread_id}
                </span>
              </div>

              <p className="text-xs sm:text-sm text-amber-100 leading-relaxed">
                {hitlInterrupt.reason}
              </p>

              <div className="flex flex-wrap gap-2">
                {hitlInterrupt.triggered_policy_ids.map((pid) => (
                  <button
                    key={pid}
                    type="button"
                    onClick={() => jumpToCitation(pid)}
                    className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-amber-500/40 text-amber-300 hover:bg-slate-800"
                  >
                    View Policy [{pid}] →
                  </button>
                ))}
              </div>

              <div>
                <label className="block text-[11px] font-mono text-amber-200/80 mb-1">
                  Optional Audit Trail Sign-Off Note:
                </label>
                <input
                  type="text"
                  value={reviewerNote}
                  onChange={(e) => setReviewerNote(e.target.value)}
                  placeholder="e.g., Enforce 15% unleveraged retail cap before publishing to TradingTackle..."
                  className="w-full rounded-lg bg-slate-950/90 border border-amber-500/40 px-3 py-2 text-xs text-white focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                {hitlInterrupt.available_actions.map((act) => {
                  const isRec = act.id === 'tighten_risk_parameters';
                  const isDanger = act.id === 'reject_publication';
                  return (
                    <button
                      key={act.id}
                      type="button"
                      disabled={isStreaming}
                      onClick={() => handleResumeHitl(act.id)}
                      className={`text-left rounded-xl border p-3 transition ${
                        isRec
                          ? 'bg-emerald-600/20 border-emerald-400 hover:bg-emerald-600/30 text-white'
                          : isDanger
                            ? 'bg-red-950/30 border-red-500/50 hover:bg-red-950/50 text-red-100'
                            : 'bg-slate-900/90 border-amber-500/40 hover:bg-slate-800 text-slate-100'
                      }`}
                    >
                      <div className="text-xs font-bold">{act.label}</div>
                      <p className="text-[11px] text-slate-300 mt-1 leading-snug">
                        {act.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* Side-by-Side Comparison: Naive Single-LLM vs Gardoon Multi-Agent */}
          {naiveComparison && (
            <section className="rounded-2xl bg-surface-elevated border border-cyan-500/40 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-cyan-400" />
                  Benchmark: Generic Single-LLM Prompt vs. Gardoon Multi-Agent Pipeline
                </h3>
                <button
                  type="button"
                  onClick={() => setNaiveComparison(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Close ✕
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
                <div className="rounded-xl bg-red-950/15 border border-red-500/30 p-3.5 space-y-2">
                  <div className="font-mono text-[11px] text-red-300 font-semibold">
                    ✗ {naiveComparison.naive_model}
                  </div>
                  <p className="text-slate-300 italic text-[11px] leading-relaxed bg-slate-950/70 p-2.5 rounded-lg border border-slate-800">
                    &ldquo;{naiveComparison.naive_output}&rdquo;
                  </p>
                  <div className="font-semibold text-red-300 pt-1">
                    Enterprise Blind Spots & Missed Risks:
                  </div>
                  <ul className="space-y-1 text-[11px] text-slate-300 list-disc pl-4">
                    {naiveComparison.missed_risks.map((risk, idx) => (
                      <li key={idx}>{risk}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl bg-emerald-950/15 border border-emerald-500/30 p-3.5 space-y-2">
                  <div className="font-mono text-[11px] text-emerald-300 font-semibold">
                    ✓ Gardoon Stateful Multi-Agent System
                  </div>
                  <ul className="space-y-2 text-[11px] text-slate-200">
                    {naiveComparison.why_multi_agent_wins.map((pt, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          )}

          {/* FINAL STRUCTURED AUDIT & STRATEGY REPORT */}
          {finalReport && (
            <section className="rounded-2xl bg-surface-elevated/90 border border-slate-800 p-5 shadow-exec space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="text-[11px] font-mono text-brand-400 uppercase">
                    Verified Multi-Agent Deliverable
                  </div>
                  <h2 className="text-lg font-extrabold text-white mt-0.5">
                    {finalReport.strategy_title}
                  </h2>
                </div>
                {verdictBadge(finalReport.compliance_verdict)}
              </div>

              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                {finalReport.executive_summary}
              </p>

              {finalReport.human_decision_applied && (
                <div className="rounded-xl bg-emerald-950/25 border border-emerald-500/40 px-3.5 py-2.5 text-xs font-mono text-emerald-200">
                  ✓ Human Governance Sign-Off Recorded:{' '}
                  {finalReport.human_decision_applied}
                </div>
              )}

              {/* 4 Empirical KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="rounded-xl bg-surface-subtle border border-slate-800 p-3">
                  <div className="text-[10px] font-mono uppercase text-slate-400">
                    Empirical Winrate
                  </div>
                  <div className="text-sm font-bold font-mono text-white mt-1">
                    {finalReport.metrics.expected_winrate_range}
                  </div>
                </div>

                <div className="rounded-xl bg-surface-subtle border border-slate-800 p-3">
                  <div className="text-[10px] font-mono uppercase text-slate-400">
                    Profit Factor Est.
                  </div>
                  <div className="text-sm font-bold font-mono text-emerald-400 mt-1">
                    {finalReport.metrics.profit_factor_estimate}
                  </div>
                </div>

                <div className="rounded-xl bg-surface-subtle border border-slate-800 p-3">
                  <div className="text-[10px] font-mono uppercase text-slate-400">
                    Est. Max Drawdown
                  </div>
                  <div
                    className={`text-sm font-bold font-mono mt-1 ${
                      finalReport.metrics.max_drawdown_est_pct > 20
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    {finalReport.metrics.max_drawdown_est_pct.toFixed(1)}%
                  </div>
                </div>

                <div className="rounded-xl bg-surface-subtle border border-slate-800 p-3">
                  <div className="text-[10px] font-mono uppercase text-slate-400">
                    Repaint & Friction
                  </div>
                  <div className="text-xs font-bold font-mono text-cyan-300 mt-1">
                    {finalReport.metrics.repainting_clean
                      ? 'Clean · 6bps+2t'
                      : 'Flagged'}
                  </div>
                </div>
              </div>

              {/* Grounded Audit Findings */}
              <div className="space-y-2.5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" /> Grounded
                  Audit & Compliance Findings ({finalReport.findings.length})
                </h3>
                <div className="space-y-2">
                  {finalReport.findings.map((f, idx) => {
                    const sevStyle =
                      f.severity === 'critical'
                        ? 'border-red-500/40 bg-red-950/15 text-red-300'
                        : f.severity === 'warning'
                          ? 'border-amber-500/40 bg-amber-950/15 text-amber-300'
                          : 'border-emerald-500/30 bg-emerald-950/10 text-emerald-300';
                    return (
                      <div
                        key={`${f.rule_id}-${idx}`}
                        className="rounded-xl bg-surface-subtle border border-slate-800/90 p-3.5 text-xs space-y-1.5"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded border ${sevStyle}`}
                            >
                              {f.severity}
                            </span>
                            <span className="font-bold text-white">
                              {f.title}
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => jumpToCitation(f.cited_doc_id)}
                            className="font-mono text-[11px] px-2 py-0.5 rounded bg-brand-500/15 border border-brand-500/30 text-brand-300 hover:bg-brand-500/25 transition"
                          >
                            Cite [{f.cited_doc_id}] →
                          </button>
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {f.explanation}
                        </p>
                        <p className="text-[11px] font-mono text-emerald-400/90">
                          ↳ Remediation: {f.remediation}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Verified Pine Script v5 Output */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-emerald-400" /> Certified
                    Pine Script v5 Deliverable
                  </h3>
                  <button
                    type="button"
                    onClick={copyPineCode}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-mono text-slate-200 transition"
                  >
                    {copiedCode ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" /> Copy Pine v5
                      </>
                    )}
                  </button>
                </div>
                <pre className="rounded-xl bg-slate-950 border border-slate-800 p-4 text-[11px] sm:text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed max-h-96">
                  <code>{finalReport.pine_script_v5_code}</code>
                </pre>
              </div>
            </section>
          )}
        </div>

        {/* RIGHT COLUMN (5 cols): Sticky Glass-Box Engineering Inspector */}
        <aside className="lg:col-span-5 lg:sticky lg:top-28 space-y-3">
          <div className="rounded-2xl bg-surface-elevated/80 border border-slate-800/90 p-2 flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setInspectorTab('graph')}
              className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl text-xs font-semibold transition ${
                inspectorTab === 'graph'
                  ? 'bg-brand-600 text-white shadow-glow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              Live LangGraph
            </button>

            <button
              type="button"
              onClick={() => setInspectorTab('vector')}
              className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl text-xs font-semibold transition ${
                inspectorTab === 'vector'
                  ? 'bg-brand-600 text-white shadow-glow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Qdrant Hybrid DB
              {retrievedChunks.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-950/70 text-emerald-300 font-mono">
                  {retrievedChunks.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setInspectorTab('k8s')}
              className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl text-xs font-semibold transition ${
                inspectorTab === 'k8s'
                  ? 'bg-brand-600 text-white shadow-glow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Cloud & K8s
            </button>
          </div>

          {inspectorTab === 'graph' && (
            <GraphVisualizer
              activeNodes={activeNodes}
              completedNodes={completedNodes}
              isInterrupted={hitlInterrupt !== null}
              correctionLoops={correctionLoops}
              traces={traces}
              totalLatencyMs={totalLatencyMs}
              totalCostUsd={totalCostUsd}
            />
          )}

          {inspectorTab === 'vector' && (
            <VectorInspector
              runChunks={retrievedChunks}
              highlightedDocId={highlightedDocId}
            />
          )}

          {inspectorTab === 'k8s' && (
            <KubernetesBlueprint telemetry={telemetry} />
          )}
        </aside>
      </main>

      {/* Executive Footer */}
      <footer className="border-t border-slate-800/80 bg-surface-subtle/60 mt-12">
        <div className="max-w-[1480px] mx-auto px-4 sm:px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <div>
            © {new Date().getFullYear()}{' '}
            <a
              href="https://gardoon.ltd"
              target="_blank"
              rel="noreferrer"
              className="text-slate-200 font-semibold hover:text-brand-400"
            >
              Gardoon Ltd.
            </a>{' '}
            — Custom Multi-Agent AI Systems, Hybrid RAG & Cloud-Native SaaS Engineering.
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <a
              href="https://github.com/markus-antonius-wirtz/gardoon-agentic-ai-showcase"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition"
            >
              <Code2 className="w-3.5 h-3.5 text-emerald-400" />
              GitHub &amp; K8s Helm
            </a>

            <a
              href="https://tradingtackle.ai"
              target="_blank"
              rel="noreferrer"
              className="hover:text-white transition"
            >
              TradingTackle.ai
            </a>
            <a
              href="https://gardoon.ltd"
              target="_blank"
              rel="noreferrer"
              className="hover:text-white transition"
            >
              Corporate Site & Imprint
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
