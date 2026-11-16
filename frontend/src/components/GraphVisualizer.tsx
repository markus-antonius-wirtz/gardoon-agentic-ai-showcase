'use client';

import React from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  GitBranch,
  PauseCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { TraceStep } from '@/types/showcase';

interface GraphVisualizerProps {
  activeNodes: string[];
  completedNodes: string[];
  isInterrupted: boolean;
  correctionLoops: number;
  traces: TraceStep[];
  totalLatencyMs: number | null;
  totalCostUsd: number;
}

interface NodeMeta {
  id: string;
  title: string;
  role: string;
  patternBadge: string;
  icon: React.ReactNode;
}

const NODES_TOP: NodeMeta = {
  id: 'intake_supervisor',
  title: '1. Intake Supervisor',
  role: 'Intent Triage & Static Trap Pre-Scan',
  patternBadge: 'LangGraph Send() Router',
  icon: <GitBranch className="w-4 h-4" />,
};

const PARALLEL_NODES: NodeMeta[] = [
  {
    id: 'retrieve_pine_docs',
    title: '2a. Pine v5 Docs RAG',
    role: 'Dense 3072d + BM25 -> RRF',
    patternBadge: 'Track A',
    icon: <Database className="w-4 h-4" />,
  },
  {
    id: 'retrieve_risk_policies',
    title: '2b. Risk Policy RAG',
    role: 'MiFID & Audit Standards RRF',
    patternBadge: 'Track B',
    icon: <Database className="w-4 h-4" />,
  },
];

const SEQUENTIAL_NODES: NodeMeta[] = [
  {
    id: 'quant_architect',
    title: '3. Quant & Pine v5 Architect',
    role: 'Grounded Code & Metrics Synthesis',
    patternBadge: 'Smart Model Routing',
    icon: <Sparkles className="w-4 h-4" />,
  },
  {
    id: 'audit_critic',
    title: '4. Four-Eyes Audit Critic',
    role: 'AST Compiler + Citation Guardrails',
    patternBadge: 'Self-Correction Loop',
    icon: <ShieldCheck className="w-4 h-4" />,
  },
  {
    id: 'human_governance_gate',
    title: '5. Human Governance Gate',
    role: 'Policy TT-RISK-002 (>20% Max DD)',
    patternBadge: 'Stateful interrupt()',
    icon: <PauseCircle className="w-4 h-4" />,
  },
  {
    id: 'final_publisher',
    title: '6. Final Report Publisher',
    role: 'Immutable Audit & Provenance Seal',
    patternBadge: 'Pydantic v2 Strict',
    icon: <CheckCircle2 className="w-4 h-4" />,
  },
];

export function GraphVisualizer({
  activeNodes,
  completedNodes,
  isInterrupted,
  correctionLoops,
  traces,
  totalLatencyMs,
  totalCostUsd,
}: GraphVisualizerProps) {
  const latestTraceFor = (nodeId: string) =>
    [...traces].reverse().find((t) => t.node === nodeId);

  const renderNodeCard = (node: NodeMeta) => {
    const isPausedHere = isInterrupted && node.id === 'human_governance_gate';
    const isActive = activeNodes.includes(node.id);
    const isDone = completedNodes.includes(node.id);
    const trace = latestTraceFor(node.id);

    let borderStyle = 'border-slate-800/90 bg-surface-subtle/80 text-slate-400';
    let dotStyle = 'bg-slate-700';

    if (isPausedHere) {
      borderStyle =
        'border-amber-500/80 bg-amber-950/25 text-amber-100 shadow-glow-amber ring-1 ring-amber-400/40';
      dotStyle = 'bg-amber-400 animate-ping';
    } else if (isActive) {
      borderStyle =
        'border-brand-500 bg-brand-950/35 text-white shadow-glow-sm ring-1 ring-brand-400/40';
      dotStyle = 'bg-brand-400 animate-ping';
    } else if (isDone) {
      borderStyle = 'border-emerald-500/45 bg-emerald-950/15 text-slate-100';
      dotStyle = 'bg-emerald-400';
    }

    return (
      <div
        key={node.id}
        className={`rounded-xl border p-3 transition-all duration-300 ${borderStyle}`}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className={`h-2.5 w-2.5 rounded-full ${dotStyle}`} />
            </span>
            <span className="text-brand-400 shrink-0">{node.icon}</span>
            <span className="font-semibold text-xs sm:text-sm truncate">
              {node.title}
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-900/90 border border-slate-700/70 text-slate-300 shrink-0">
            {node.patternBadge}
          </span>
        </div>

        <p className="text-[11px] text-slate-400 mt-1 pl-4">{node.role}</p>

        {isPausedHere && (
          <div className="mt-2 ml-4 text-[11px] font-mono text-amber-300 bg-amber-950/50 border border-amber-500/40 rounded-lg px-2.5 py-1.5">
            ⏸ Suspended in Checkpointer — awaiting Human Risk Officer action on left panel...
          </div>
        )}

        {trace && (
          <div className="mt-2 ml-4 pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-300">
            <span className="truncate max-w-[240px] text-cyan-300/90">
              {trace.model_used}
            </span>
            <span className="text-emerald-400">{trace.latency_ms} ms</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Top Runtime Metrics Bar */}
      <div className="grid grid-cols-3 gap-2.5">
        <div className="rounded-xl bg-surface-subtle border border-slate-800/80 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Activity className="w-3 h-3 text-brand-400" /> Nodes Executed
          </div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {traces.length}
            {correctionLoops > 0 && (
              <span className="ml-1.5 text-xs text-amber-400 font-normal">
                (+{correctionLoops} retry)
              </span>
            )}
          </div>
        </div>

        <div className="rounded-xl bg-surface-subtle border border-slate-800/80 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3 text-emerald-400" /> E2E Latency
          </div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {totalLatencyMs !== null
              ? `${(totalLatencyMs / 1000).toFixed(2)}s`
              : isInterrupted
                ? 'Paused'
                : traces.length > 0
                  ? 'Streaming…'
                  : 'Ready'}
          </div>
        </div>

        <div className="rounded-xl bg-surface-subtle border border-slate-800/80 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-400" /> Est. Token Cost
          </div>
          <div className="text-base font-bold font-mono text-emerald-400 mt-0.5">
            ${totalCostUsd.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Live Visual DAG */}
      <div className="rounded-2xl bg-surface-elevated/60 border border-slate-800/90 p-3.5 space-y-2.5">
        <div className="flex items-center justify-between text-xs text-slate-400 pb-1">
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <RefreshCw
              className={`w-3.5 h-3.5 text-brand-400 ${
                activeNodes.length > 0 ? 'animate-spin' : ''
              }`}
            />
            Stateful LangGraph Execution Topology
          </span>
          <span className="font-mono text-[11px] text-slate-400">
            StateGraph + Send() + interrupt()
          </span>
        </div>

        {renderNodeCard(NODES_TOP)}

        <div className="flex items-center justify-center text-[10px] font-mono text-brand-400/90 py-0.5">
          ↙ Parallel Map-Reduce Fan-Out (Send API) ↘
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {PARALLEL_NODES.map(renderNodeCard)}
        </div>

        <div className="flex items-center justify-center text-[10px] font-mono text-emerald-400/90 py-0.5">
          ↘ Annotated Reducer Join (operator.add) ↙
        </div>

        <div className="space-y-2.5">{SEQUENTIAL_NODES.map(renderNodeCard)}</div>
      </div>

      {/* Live Chronological Event Stream */}
      <div className="rounded-2xl bg-surface-subtle border border-slate-800/90 p-3.5">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5">
          Real-Time Node Execution Trace (SSE)
        </h4>
        {traces.length === 0 ? (
          <p className="text-xs text-slate-500 font-mono py-4 text-center">
            Select a scenario or submit a prompt to watch live graph transitions.
          </p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {traces.map((step, idx) => (
              <div
                key={`${step.node}-${idx}`}
                className="rounded-lg bg-slate-900/80 border border-slate-800/80 p-2.5 text-xs font-mono"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-brand-400 font-semibold">
                    [{idx + 1}] {step.node}
                  </span>
                  <span className="text-slate-400">
                    {step.latency_ms}ms · ${step.cost_usd_est.toFixed(4)}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] mt-1 leading-relaxed">
                  {step.detail}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
