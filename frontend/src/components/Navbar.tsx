'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, User as UserIcon, LogOut, Building } from 'lucide-react';
import { clearAuthToken, getUserInfo } from '@/lib/api';

export default function Navbar() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; roles: string[]; department: string } | null>(null);

  useEffect(() => {
    const info = getUserInfo();
    if (info) {
      setUser(info);
    }
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    router.push('/login');
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-slate-300">Production Enterprise Knowledge Assistant</h2>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          RBAC Protected
        </span>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-xs">
              {user.email[0].toUpperCase()}
            </div>
            <div className="text-xs">
              <div className="text-slate-200 font-medium">{user.email}</div>
              <div className="flex items-center gap-2 text-slate-400">
                <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-semibold">
                  <Building className="w-3 h-3" /> {user.department}
                </span>
                <span>•</span>
                <span className="text-[10px] text-purple-400 font-semibold uppercase">
                  {user.roles?.join(', ')}
                </span>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all border border-transparent hover:border-red-500/20"
          title="Sign out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
