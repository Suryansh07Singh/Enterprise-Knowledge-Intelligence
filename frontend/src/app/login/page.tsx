'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Database, ShieldCheck, ArrowRight, Lock, Mail } from 'lucide-react';
import { setAuthToken } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@enterprise.com');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.access_token);
        localStorage.setItem('user_info', JSON.stringify({
          email: data.email,
          roles: data.roles,
          department: data.department
        }));
        router.push('/');
      } else {
        const err = await res.json();
        setError(err.detail || 'Login failed');
      }
    } catch (e: any) {
      setError(`Connection error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800 rounded-3xl p-8 shadow-2xl relative z-10 backdrop-blur-xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-2xl shadow-lg shadow-cyan-500/20">
            <Database className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="font-extrabold text-white text-xl tracking-tight">KNOWLEDGE INTELLIGENCE</h1>
            <p className="text-xs text-cyan-400 font-semibold tracking-wider uppercase">Enterprise RAG Portal</p>
          </div>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">Corporate Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-all"
                placeholder="user@enterprise.com"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-all"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold py-3 px-4 rounded-xl text-xs transition-all shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2"
          >
            {loading ? 'Authenticating...' : 'Sign In to Portal'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Demo Account Quick Switcher */}
        <div className="mt-8 pt-6 border-t border-slate-800/80">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> Quick Demo Role Switcher
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleDemoLogin('admin@enterprise.com', 'admin123')}
              className="p-2.5 bg-slate-950 hover:bg-slate-800/60 border border-slate-800 rounded-xl text-left transition-all"
            >
              <div className="text-xs font-bold text-cyan-400">Admin Account</div>
              <div className="text-[10px] text-slate-500">Full RBAC (HR/Fin)</div>
            </button>
            <button
              onClick={() => handleDemoLogin('employee@enterprise.com', 'employee123')}
              className="p-2.5 bg-slate-950 hover:bg-slate-800/60 border border-slate-800 rounded-xl text-left transition-all"
            >
              <div className="text-xs font-bold text-slate-300">Employee Account</div>
              <div className="text-[10px] text-slate-500">Public Policy Only</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
