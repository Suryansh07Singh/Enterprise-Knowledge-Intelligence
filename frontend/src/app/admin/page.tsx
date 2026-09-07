'use client';

import React, { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import { ShieldAlert, Play, BarChart2, CheckCircle, Clock, Cpu, Award, Zap } from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';

interface EvalRun {
  id: string;
  name: string;
  recall_at_k: number;
  precision_at_k: number;
  mrr: number;
  ndcg: number;
  faithfulness_score: number;
  total_eval_questions: number;
  duration_seconds: number;
  created_at: string;
}

export default function AdminPage() {
  const [evalRuns, setEvalRuns] = useState<EvalRun[]>([]);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const loadEvalResults = async () => {
    try {
      const res = await fetchWithAuth('/evaluation/results');
      if (res.ok) {
        const data = await res.json();
        setEvalRuns(data);
      }
    } catch (e) {
      console.error('Eval load error:', e);
    }
  };

  useEffect(() => {
    loadEvalResults();
  }, []);

  const handleRunBenchmark = async () => {
    setRunning(true);
    setStatus('Running 100+ Enterprise Question Benchmark across Dense, Sparse, Hybrid, & Rerank modes...');
    try {
      const res = await fetchWithAuth('/evaluation/run', {
        method: 'POST',
        body: JSON.stringify({
          name: 'Enterprise IR Quality Benchmark',
          modes: ['hybrid_rerank', 'hybrid', 'dense', 'sparse'],
        }),
      });

      if (res.ok) {
        setStatus('Benchmark evaluation completed successfully!');
        loadEvalResults();
      } else {
        const err = await res.json();
        setStatus(`Error: ${err.detail || 'Benchmark execution failed'}`);
      }
    } catch (e: any) {
      setStatus(`Exception: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex bg-slate-950 min-h-screen font-sans text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />

        <main className="p-8 space-y-8 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Admin & Evaluation Console</h1>
              <p className="text-sm text-slate-400 mt-1">Quantitative evaluation metrics (Recall@K, MRR, nDCG, Faithfulness) & experiments.</p>
            </div>

            <button
              onClick={handleRunBenchmark}
              disabled={running}
              className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-bold px-5 py-2.5 rounded-xl text-xs transition-all shadow-lg shadow-cyan-500/20"
            >
              <Play className="w-4 h-4" />
              {running ? 'Evaluating Harness...' : 'Run 100+ Question Benchmark'}
            </button>
          </div>

          {status && (
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl text-xs text-cyan-400 flex items-center gap-2">
              <Clock className="w-4 h-4 animate-pulse" /> {status}
            </div>
          )}

          {/* Benchmark Runs Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-400" /> Evaluation Benchmark Experiment Results
              </h3>
              <span className="text-xs text-slate-400 font-mono">{evalRuns.length} runs recorded</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Experiment Name</th>
                    <th className="px-6 py-4">Recall@5</th>
                    <th className="px-6 py-4">Precision@5</th>
                    <th className="px-6 py-4">MRR</th>
                    <th className="px-6 py-4">nDCG@5</th>
                    <th className="px-6 py-4">Faithfulness</th>
                    <th className="px-6 py-4">Questions</th>
                    <th className="px-6 py-4">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {evalRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-6 py-4 font-bold text-white">{run.name}</td>
                      <td className="px-6 py-4 font-mono font-bold text-cyan-400">{(run.recall_at_k * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4 font-mono font-bold text-blue-400">{(run.precision_at_k * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4 font-mono font-bold text-purple-400">{run.mrr.toFixed(3)}</td>
                      <td className="px-6 py-4 font-mono font-bold text-amber-400">{run.ndcg.toFixed(3)}</td>
                      <td className="px-6 py-4 font-mono font-bold text-emerald-400">{(run.faithfulness_score * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4 font-mono">{run.total_eval_questions}</td>
                      <td className="px-6 py-4 font-mono text-slate-500">{run.duration_seconds}s</td>
                    </tr>
                  ))}
                  {evalRuns.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-6 py-8 text-center text-slate-500">
                        No benchmark evaluation runs executed yet. Click "Run 100+ Question Benchmark" to begin.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* System Architecture Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-900/60 border border-slate-800 p-6 rounded-2xl space-y-2">
              <h4 className="font-bold text-white text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-cyan-400" /> Dense + BM25 RRF Trade-off
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Combining Qdrant semantic dense embeddings with BM25 sparse exact keyword indices ensures high recall for conceptual queries while preserving exact match accuracy for technical codes (e.g. IT-204).
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-6 rounded-2xl space-y-2">
              <h4 className="font-bold text-white text-sm flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" /> Cross-Encoder Reranking
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ms-marco Cross-Encoder scores (Query, Chunk) pairs jointly, filtering initial hybrid candidates (top 25) down to top 5 context windows to prevent context overflow.
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-6 rounded-2xl space-y-2">
              <h4 className="font-bold text-white text-sm flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-emerald-400" /> RBAC & Guardrails
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Metadata security payload filters guarantee unauthorized chunks never enter candidate sets, while XML context tagging mitigates prompt injection attempts.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
