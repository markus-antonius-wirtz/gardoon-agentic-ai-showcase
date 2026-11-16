'use client';

import React from 'react';
import { Box, Cloud, HardDrive, Layers, Server, Shield } from 'lucide-react';
import { SystemTelemetry } from '@/types/showcase';

interface KubernetesBlueprintProps {
  telemetry: SystemTelemetry | null;
}

export function KubernetesBlueprint({ telemetry }: KubernetesBlueprintProps) {
  return (
    <div className="space-y-4">
      {/* Live Runtime Pod & Persistence Telemetry */}
      <div className="rounded-2xl bg-surface-subtle border border-slate-800/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-emerald-400" /> Live Container &
            Cluster Telemetry
          </h4>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            {telemetry ? telemetry.status.toUpperCase() : 'CONNECTING'}
          </span>
        </div>

        {telemetry ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs font-mono">
            <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
              <span className="text-[10px] text-slate-400 block">POD / INSTANCE ID</span>
              <span className="text-brand-300 truncate block mt-0.5">
                {telemetry.pod_name}
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
              <span className="text-[10px] text-slate-400 block">NAMESPACE · TOPOLOGY</span>
              <span className="text-slate-200 truncate block mt-0.5">
                {telemetry.namespace} ({telemetry.cluster_topology})
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
              <span className="text-[10px] text-slate-400 block">CHECKPOINTER STATE</span>
              <span className="text-emerald-300 truncate block mt-0.5">
                {telemetry.checkpointer_backend}
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
              <span className="text-[10px] text-slate-400 block">QDRANT VECTOR INDEX</span>
              <span className="text-cyan-300 truncate block mt-0.5">
                {telemetry.indexed_documents} docs · {telemetry.vector_dimensions}d ({telemetry.qdrant_mode})
              </span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500 font-mono">Loading live pod metrics…</p>
        )}
      </div>

      {/* Production Helm & Cloud Blueprint */}
      <div className="rounded-2xl bg-surface-elevated/60 border border-slate-800/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Cloud className="w-3.5 h-3.5 text-brand-400" /> Kubernetes Helm
            Chart Architecture
          </h4>
          <span className="text-[10px] font-mono text-slate-400">
            deploy/helm/gardoon-agent-showcase
          </span>
        </div>

        <div className="space-y-2 text-xs">
          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-3 flex items-start gap-3">
            <Layers className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-200">
                HorizontalPodAutoscaler + Non-Root Multi-Stage Containers
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                Stateless FastAPI SSE orchestrator & Next.js standalone UI scale
                from 2 to 8 replicas (70% CPU target) with zero-buffering Ingress
                streaming annotations.
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-3 flex items-start gap-3">
            <HardDrive className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-200">
                Stateful Persistence: Qdrant Vector Engine + PostgreSQL 16
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                LangGraph <code className="text-emerald-300">AsyncPostgresSaver</code>{' '}
                persists interrupted Human-in-the-Loop threads across pod restarts,
                paired with PVC-backed Qdrant hybrid storage.
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-3 flex items-start gap-3">
            <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-200">
                Zero-Trust NetworkPolicy & Model-Agnostic LLM Gateway
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                Restricts database ingress strictly to orchestrator pods; supports
                1-line switching between Google Vertex/Gemini EU, Azure OpenAI
                Frankfurt, or air-gapped on-premise vLLM.
              </p>
            </div>
          </div>
        </div>

        {telemetry && (
          <div className="rounded-xl bg-slate-950/90 border border-slate-800 p-3 font-mono text-[11px] text-slate-300">
            <div className="text-slate-400 mb-1 flex items-center gap-1.5">
              <Box className="w-3.5 h-3.5 text-brand-400" /> Active Smart Model
              Routing Table
            </div>
            {Object.entries(telemetry.models_configured).map(([role, mdl]) => (
              <div key={role} className="flex justify-between py-0.5">
                <span className="text-slate-400">{role}:</span>
                <span className="text-brand-300">{mdl}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
