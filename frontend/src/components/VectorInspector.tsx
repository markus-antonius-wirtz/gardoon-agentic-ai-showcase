'use client';

import React, { useState } from 'react';
import { Database, Filter, Lock, Search, Sparkles } from 'lucide-react';
import { RetrievedChunk } from '@/types/showcase';

interface VectorInspectorProps {
  runChunks: RetrievedChunk[];
  highlightedDocId: string | null;
}

export function VectorInspector({
  runChunks,
  highlightedDocId,
}: VectorInspectorProps) {
  const [searchQuery, setSearchQuery] = useState(
    'request.security lookahead_on repainting'
  );
  const [tenant, setTenant] = useState<'tradingtackle' | 'gardoon_cloud'>(
    'tradingtackle'
  );
  const [sandboxResults, setSandboxResults] = useState<RetrievedChunk[] | null>(
    null
  );
  const [searching, setSearching] = useState(false);

  const handleInteractiveSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const params = new URLSearchParams({
        q: searchQuery.trim(),
        tenant,
        top_k: '5',
      });
      const res = await fetch(`/api/knowledge/search?${params.toString()}`);
      if (res.ok) {
        const data: RetrievedChunk[] = await res.json();
        setSandboxResults(data);
      }
    } finally {
      setSearching(false);
    }
  };

  const displayedChunks = sandboxResults ?? runChunks;

  return (
    <div className="space-y-4">
      {/* Architecture Explainer Pill */}
      <div className="rounded-xl bg-brand-950/25 border border-brand-500/30 p-3 text-xs text-slate-300 leading-relaxed">
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-brand-300 flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" /> Qdrant Hybrid Retrieval Engine
          </span>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-emerald-400">
            Dense + Sparse BM25 → RRF
          </span>
        </div>
        Combines <strong>3072-d Gemini Semantic Embeddings</strong> with{' '}
        <strong>BM25 Sparse Identifier Matching</strong> via{' '}
        <code className="text-cyan-300">Fusion.RRF</code> and strict{' '}
        <code className="text-cyan-300">tenant</code> payload isolation.
      </div>

      {/* Live Multi-Tenant Hybrid Search Sandbox */}
      <form
        onSubmit={handleInteractiveSearch}
        className="rounded-2xl bg-surface-subtle border border-slate-800/90 p-3.5 space-y-2.5"
      >
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-cyan-400" /> Interactive Vector
            & Multi-Tenant Isolation Probe
          </span>
          {sandboxResults !== null && (
            <button
              type="button"
              onClick={() => setSandboxResults(null)}
              className="text-[11px] text-brand-400 hover:underline"
            >
              Reset to Agent Run Chunks ({runChunks.length})
            </button>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs">
            <Lock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <select
              value={tenant}
              onChange={(e) => {
                const nextTenant = e.target.value as
                  | 'tradingtackle'
                  | 'gardoon_cloud';
                setTenant(nextTenant);
                if (nextTenant === 'gardoon_cloud') {
                  setSearchQuery('Kubernetes HPA PodDisruptionBudget Qdrant');
                } else {
                  setSearchQuery('request.security lookahead_on repainting');
                }
              }}
              className="bg-transparent text-slate-200 font-mono text-xs focus:outline-none"
            >
              <option value="tradingtackle" className="bg-slate-900">
                tenant: tradingtackle
              </option>
              <option value="gardoon_cloud" className="bg-slate-900">
                tenant: gardoon_cloud
              </option>
            </select>
          </div>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Query Qdrant hybrid index..."
            className="flex-1 bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
          />

          <button
            type="submit"
            disabled={searching}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white transition disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" />
            {searching ? 'Querying…' : 'Probe'}
          </button>
        </div>
      </form>

      {/* Retrieved Chunks & Score Breakdown */}
      <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
        {displayedChunks.length === 0 ? (
          <div className="rounded-2xl bg-surface-subtle border border-slate-800/80 p-6 text-center text-xs text-slate-400 font-mono">
            Run a scenario on the left or click &ldquo;Probe&rdquo; above to
            inspect live Dense + Sparse BM25 + RRF scores.
          </div>
        ) : (
          displayedChunks.map((chunk, i) => {
            const isHighlighted = highlightedDocId === chunk.doc_id;
            return (
              <div
                key={`${chunk.doc_id}-${i}`}
                className={`rounded-xl border p-3.5 transition-all ${
                  isHighlighted
                    ? 'border-brand-400 bg-brand-950/30 shadow-glow-sm'
                    : 'border-slate-800/90 bg-surface-subtle/90'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-brand-500/20 border border-brand-400/40 text-brand-300">
                      {chunk.doc_id}
                    </span>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                      {chunk.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> RRF {(chunk.rrf_score * 100).toFixed(0)}%
                  </span>
                </div>

                <h5 className="text-xs font-semibold text-white mt-2">
                  {chunk.title}
                </h5>

                {/* Score Bars */}
                <div className="grid grid-cols-2 gap-3 mt-2.5 text-[10px] font-mono">
                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Dense Semantic</span>
                      <span className="text-brand-300">
                        {(chunk.dense_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full"
                        style={{
                          width: `${Math.min(100, Math.max(8, chunk.dense_score * 100))}%`,
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Sparse BM25</span>
                      <span className="text-cyan-300">
                        {(chunk.sparse_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-cyan-400 rounded-full"
                        style={{
                          width: `${Math.min(100, Math.max(6, chunk.sparse_score * 100))}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                <p className="text-[11px] text-slate-300 mt-2.5 leading-relaxed">
                  {chunk.excerpt}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
