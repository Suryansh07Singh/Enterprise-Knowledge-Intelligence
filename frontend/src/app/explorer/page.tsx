'use client';

import React, { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import { Search, FileText, Layers, ShieldCheck, Sparkles } from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';

interface SearchResult {
  chunk_id: string;
  document_name: string;
  text: string;
  page_number: number;
  section_title: string;
  department: string;
  access_level: string;
  score: number;
  dense_score?: number;
  sparse_score?: number;
  rerank_score?: number;
}

export default function ExplorerPage() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid_rerank');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await fetchWithAuth('/search', {
        method: 'POST',
        body: JSON.stringify({ query, mode, top_k: 15 }),
      });

      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
        setLatency(data.latency_ms);
      }
    } catch (e) {
      console.error('Search error:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex bg-slate-950 min-h-screen font-sans text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />

        <main className="p-8 space-y-8 max-w-7xl mx-auto w-full">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Knowledge Explorer</h1>
            <p className="text-sm text-slate-400 mt-1">Direct multi-vector & sparse keyword candidate set inspection.</p>
          </div>

          {/* Search Bar & Controls */}
          <form onSubmit={handleSearch} className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex items-center gap-4 shadow-xl">
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-slate-500 absolute left-4 top-3.5" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search policy terms, codes (e.g. 'IT-204'), or reimbursement limits..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-all"
              />
            </div>

            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs text-cyan-400 font-semibold focus:outline-none"
            >
              <option value="hybrid_rerank">Hybrid + Cross-Encoder</option>
              <option value="hybrid">Hybrid (Dense + Sparse RRF)</option>
              <option value="dense">Dense Vector Only</option>
              <option value="sparse">Sparse BM25 Only</option>
            </select>

            <button
              type="submit"
              disabled={loading}
              className="bg-cyan-500 hover:bg-cyan-400 font-bold text-slate-950 px-6 py-3 rounded-xl text-xs transition-all shadow-lg shadow-cyan-500/20"
            >
              {loading ? 'Searching...' : 'Explore Chunks'}
            </button>
          </form>

          {/* Results Metadata */}
          {latency !== null && (
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Found <strong className="text-cyan-400 font-mono">{results.length}</strong> matching candidate chunks</span>
              <span className="font-mono text-slate-500">Pipeline Latency: {latency} ms</span>
            </div>
          )}

          {/* Search Results List */}
          <div className="space-y-4">
            {results.map((r, i) => (
              <div key={i} className="bg-slate-900/60 border border-slate-800/80 p-6 rounded-2xl space-y-3 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-cyan-400" />
                    <div>
                      <h4 className="font-bold text-white text-sm">{r.document_name}</h4>
                      <div className="text-xs text-slate-400">Page {r.page_number} • Section: {r.section_title}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-xs">
                    {r.rerank_score != null && (
                      <span className="px-2.5 py-1 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/30">
                        Rerank Score: {r.rerank_score.toFixed(4)}
                      </span>
                    )}
                    {r.sparse_score != null && (
                      <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        BM25: {r.sparse_score.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-300 bg-slate-950/80 p-4 rounded-xl border border-slate-800 font-mono leading-relaxed">
                  {r.text}
                </p>

                <div className="flex items-center gap-4 text-[11px] text-slate-500">
                  <span>Department: <strong className="text-slate-400">{r.department}</strong></span>
                  <span>•</span>
                  <span>RBAC Access: <strong className="text-slate-400 uppercase">{r.access_level}</strong></span>
                </div>
              </div>
            ))}

            {results.length === 0 && !loading && (
              <div className="text-center py-16 text-slate-500 text-xs">
                Enter a search query to inspect dense vector and BM25 sparse retrieval candidate chunks.
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
