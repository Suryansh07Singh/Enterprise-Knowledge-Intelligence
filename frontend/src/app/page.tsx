'use client';

import React, { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import { FileText, Upload, CheckCircle2, Clock, AlertCircle, Trash2, RefreshCw, Zap, Layers, BarChart3 } from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';

interface DocumentItem {
  id: string;
  name: string;
  file_type: string;
  size_bytes: number;
  department: string;
  access_level: string;
  version: string;
  total_pages: number;
  status: string;
  created_at: string;
}

interface Metrics {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
  avg_latency_ms: number;
  cache_hit_rate: number;
  active_users: number;
}

export default function Dashboard() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [department, setDepartment] = useState('Finance');
  const [accessLevel, setAccessLevel] = useState('employee');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const docRes = await fetchWithAuth('/documents');
      if (docRes.ok) {
        const dData = await docRes.json();
        setDocs(dData);
      }

      const metRes = await fetchWithAuth('/metrics');
      if (metRes.ok) {
        const mData = await metRes.json();
        setMetrics(mData);
      }
    } catch (e) {
      console.error('Data load error:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadStatus('Uploading file...');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('department', department);
    formData.append('access_level', accessLevel);

    try {
      const res = await fetchWithAuth('/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const job = await res.json();
        setUploadStatus(`Processing document (Job ID: ${job.job_id.slice(0, 8)})...`);
        
        // Poll job status
        const interval = setInterval(async () => {
          const jRes = await fetchWithAuth(`/jobs/${job.job_id}`);
          if (jRes.ok) {
            const jData = await jRes.json();
            if (jData.status === 'COMPLETED') {
              clearInterval(interval);
              setUploading(false);
              setUploadStatus('Document successfully processed and indexed!');
              setSelectedFile(null);
              loadData();
            } else if (jData.status === 'FAILED') {
              clearInterval(interval);
              setUploading(false);
              setUploadStatus(`Ingestion failed: ${jData.error_message}`);
            }
          }
        }, 1500);

      } else {
        const err = await res.json();
        setUploadStatus(`Error: ${err.detail || 'Upload failed'}`);
        setUploading(false);
      }
    } catch (err: any) {
      setUploadStatus(`Upload exception: ${err.message}`);
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document from vector and sparse indexes?')) return;
    try {
      const res = await fetchWithAuth(`/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        loadData();
      }
    } catch (e) {
      console.error('Delete error:', e);
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
              <h1 className="text-2xl font-bold text-white tracking-tight">Enterprise Knowledge Dashboard</h1>
              <p className="text-sm text-slate-400 mt-1">Real-time status of document ingestion, vector chunks, and system health.</p>
            </div>
            <button
              onClick={loadData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-700 transition-all"
            >
              <RefreshCw className="w-4 h-4" /> Refresh Status
            </button>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-[#121827] grid-cols-1 md:grid-cols-4 gap-5">
            <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
              <div className="flex items-center justify-between text-slate-400 mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Documents</span>
                <FileText className="w-5 h-5 text-cyan-400" />
              </div>
              <div className="text-3xl font-extrabold text-white">{metrics?.total_documents ?? 0}</div>
              <div className="text-xs text-slate-500 mt-2">Heterogeneous Knowledge Base</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
              <div className="flex items-center justify-between text-slate-400 mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider">Indexed Chunks</span>
                <Layers className="w-5 h-5 text-purple-400" />
              </div>
              <div className="text-3xl font-extrabold text-white">{metrics?.total_chunks ?? 0}</div>
              <div className="text-xs text-slate-500 mt-2">Qdrant Vector + BM25 Sparse</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
              <div className="flex items-center justify-between text-slate-400 mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider">Avg Latency</span>
                <Zap className="w-5 h-5 text-amber-400" />
              </div>
              <div className="text-3xl font-extrabold text-white">{metrics?.avg_latency_ms ?? 0} ms</div>
              <div className="text-xs text-slate-500 mt-2">RRF Fusion + Reranking</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
              <div className="flex items-center justify-between text-slate-400 mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider">Queries Logged</span>
                <BarChart3 className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="text-3xl font-extrabold text-white">{metrics?.total_queries ?? 0}</div>
              <div className="text-xs text-slate-500 mt-2">Full Tracing Enabled</div>
            </div>
          </div>

          {/* Document Upload Card */}
          <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
            <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-cyan-400" /> Ingest Enterprise Document (Async Worker Pipeline)
            </h3>

            <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">File (PDF, DOCX, MD, TXT, HTML)</label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 bg-slate-950 border border-slate-800 rounded-xl p-2.5 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-500/10 file:text-cyan-400 hover:file:bg-cyan-500/20"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Department Target</label>
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full text-xs text-slate-200 bg-slate-950 border border-slate-800 rounded-xl p-2.5"
                >
                  <option value="Finance">Finance</option>
                  <option value="HR">HR</option>
                  <option value="Engineering">Engineering</option>
                  <option value="General">General</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">RBAC Access Permission</label>
                <select
                  value={accessLevel}
                  onChange={(e) => setAccessLevel(e.target.value)}
                  className="w-full text-xs text-slate-200 bg-slate-950 border border-slate-800 rounded-xl p-2.5"
                >
                  <option value="employee">Employee (Public)</option>
                  <option value="hr">HR Confidential</option>
                  <option value="finance">Finance Confidential</option>
                  <option value="engineering">Engineering Internal</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={uploading || !selectedFile}
                className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold py-2.5 px-4 rounded-xl text-xs transition-all flex items-center justify-center gap-2"
              >
                {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {uploading ? 'Processing Job...' : 'Start Ingestion'}
              </button>
            </form>

            {uploadStatus && (
              <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-cyan-400 flex items-center gap-2">
                <Clock className="w-4 h-4 animate-pulse" /> {uploadStatus}
              </div>
            )}
          </div>

          {/* Document Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Knowledge Documents</h3>
              <span className="text-xs text-slate-400 font-mono">{docs.length} active documents</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Document Name</th>
                    <th className="px-6 py-4">Department</th>
                    <th className="px-6 py-4">RBAC Access</th>
                    <th className="px-6 py-4">Pages</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {docs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-6 py-4 font-medium text-white flex items-center gap-3">
                        <FileText className="w-4 h-4 text-cyan-400" />
                        <div>
                          <div>{doc.name}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{(doc.size_bytes / 1024).toFixed(1)} KB • v{doc.version}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-medium">
                          {doc.department}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-md font-semibold uppercase text-[10px] ${
                          doc.access_level === 'hr' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30' :
                          doc.access_level === 'finance' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                          'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                        }`}>
                          {doc.access_level}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono">{doc.total_pages}</td>
                      <td className="px-6 py-4">
                        <span className={`flex items-center gap-1.5 font-semibold text-xs ${
                          doc.status === 'COMPLETED' ? 'text-emerald-400' :
                          doc.status === 'PROCESSING' ? 'text-amber-400 animate-pulse' : 'text-red-400'
                        }`}>
                          {doc.status === 'COMPLETED' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                          {doc.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                          title="Delete Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {docs.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                        No policy documents ingested yet. Upload a PDF/DOCX to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
