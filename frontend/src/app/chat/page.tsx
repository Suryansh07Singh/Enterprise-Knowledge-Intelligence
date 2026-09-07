'use client';

import React, { useState, useRef, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import { Send, Bot, User, Sparkles, BookOpen, CheckCircle, AlertTriangle, ChevronRight, ThumbsUp, ThumbsDown, Shield, FileText, X } from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';

interface Citation {
  document_id: string;
  document_name: string;
  page: number;
  section: string;
  excerpt: string;
  score?: number;
}

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  grounded?: boolean;
  rewritten_query?: string;
  trace_id?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      content: 'Welcome to the Enterprise Knowledge Intelligence Assistant! Ask me any question grounded strictly in our corporate policy documents.',
      grounded: true,
    },
  ]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('hybrid_rerank');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userText = query;
    setQuery('');
    const userMsg: Message = { id: Date.now().toString(), sender: 'user', content: userText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetchWithAuth('/chat', {
        method: 'POST',
        body: JSON.stringify({
          query: userText,
          conversation_id: conversationId,
          mode: mode,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setConversationId(data.conversation_id);
        const asstMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          content: data.answer,
          citations: data.citations,
          confidence: data.confidence,
          grounded: data.grounded,
          rewritten_query: data.rewritten_query,
          trace_id: data.trace_id,
        };
        setMessages((prev) => [...prev, asstMsg]);
      } else {
        const err = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: 'assistant',
            content: `Error: ${err.detail || 'Failed to generate response'}`,
            grounded: false,
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: 'assistant',
          content: `Connection error: ${err.message}`,
          grounded: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex bg-slate-950 min-h-screen font-sans text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <Navbar />

        {/* Top Control Bar */}
        <div className="bg-slate-950 border-b border-slate-800 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-300">Retrieval Pipeline Mode:</span>
          </div>

          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-cyan-400 font-semibold focus:outline-none"
          >
            <option value="hybrid_rerank">Hybrid + Cross-Encoder Rerank (Recommended)</option>
            <option value="hybrid">Hybrid Search (Dense + BM25 RRF)</option>
            <option value="dense">Dense Vector Search Only (Qdrant)</option>
            <option value="sparse">Sparse Search Only (BM25 Keyword)</option>
          </select>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl mx-auto w-full">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.sender === 'assistant' && (
                <div className="w-9 h-9 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0">
                  <Bot className="w-5 h-5" />
                </div>
              )}

              <div className={`space-y-3 max-w-2xl ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                {/* User query rewrite tag */}
                {msg.rewritten_query && (
                  <div className="text-[11px] font-mono text-cyan-400/80 bg-cyan-950/40 border border-cyan-800/40 px-3 py-1 rounded-lg">
                    🔍 Rewritten Query: "{msg.rewritten_query}"
                  </div>
                )}

                <div
                  className={`p-5 rounded-3xl text-sm leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-medium rounded-tr-none shadow-lg shadow-cyan-500/10'
                      : 'bg-slate-900/80 border border-slate-800 text-slate-200 rounded-tl-none shadow-xl'
                  }`}
                >
                  {msg.content}

                  {/* Grounded Status & Confidence */}
                  {msg.sender === 'assistant' && msg.id !== 'welcome' && (
                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                      <span className={`flex items-center gap-1.5 font-semibold ${msg.grounded ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {msg.grounded ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                        {msg.grounded ? 'Evidence Grounded' : 'Abstain / Low Evidence'}
                      </span>
                      {msg.confidence !== undefined && (
                        <span className="font-mono text-[11px] text-slate-500">
                          Confidence: {(msg.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Citations List */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 space-y-2">
                    <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                      <BookOpen className="w-3.5 h-3.5 text-cyan-400" /> Verifiable Source Citations ({msg.citations.length})
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {msg.citations.map((c, i) => (
                        <button
                          key={i}
                          onClick={() => setSelectedCitation(c)}
                          className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-left transition-all group"
                        >
                          <div className="text-xs font-semibold text-cyan-400 flex items-center justify-between group-hover:text-cyan-300">
                            <span>{c.document_name}</span>
                            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                          </div>
                          <div className="text-[11px] text-slate-400 mt-1">
                            Page {c.page} • Section: {c.section}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div className="w-9 h-9 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0">
                  <User className="w-5 h-5" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-4 items-center text-slate-400 text-xs">
              <div className="w-9 h-9 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <Bot className="w-5 h-5 animate-pulse" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                Rewriting query, running hybrid retrieval, cross-encoding, & generating grounded answer...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-6 bg-slate-950 border-t border-slate-800">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask any question about enterprise policies (e.g. 'What is international travel reimbursement limit?')..."
              className="w-full bg-slate-900 border border-slate-800 rounded-2xl pl-5 pr-14 py-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-all shadow-inner"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-3 p-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 text-slate-950 rounded-xl transition-all font-bold shadow-lg shadow-cyan-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* Source Preview Drawer Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-xl w-full p-6 space-y-4 shadow-2xl relative">
            <button
              onClick={() => setSelectedCitation(null)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-xl bg-slate-800/50"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-cyan-400" />
              <div>
                <h3 className="font-bold text-white text-base">{selectedCitation.document_name}</h3>
                <p className="text-xs text-slate-400">Page {selectedCitation.page} • Section: {selectedCitation.section}</p>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 p-4 rounded-2xl text-xs text-slate-300 font-mono leading-relaxed max-h-60 overflow-y-auto">
              {selectedCitation.excerpt}
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedCitation(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
