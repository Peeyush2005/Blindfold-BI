import React from 'react';
import { Shield, Sparkles, Database, RefreshCw, BarChart3, MessageSquare, AlertTriangle, Layers, Link2 } from 'lucide-react';

interface NavbarProps {
  activeTab: 'dashboard' | 'chat' | 'debt' | 'architecture' | 'monday';
  setActiveTab: (tab: 'dashboard' | 'chat' | 'debt' | 'architecture' | 'monday') => void;
  onRefreshData: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onRefreshData,
  isRefreshing,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-[#0c1222]/90 backdrop-blur-md border-b border-slate-800/80 px-4 lg:px-8 py-3 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">

        {/* Brand & Identity */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-fuchsia-600 p-[2px] shadow-lg shadow-indigo-500/20">
            <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Shield className="h-5 w-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-white m-0 p-0 font-sans">
                Blindfold <span className="text-cyan-400">BI</span>
              </h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/50">
                Skylark Drones
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block m-0 p-0">
              Privacy-First Conversational Intelligence & Executive Analytics
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center bg-slate-900/90 border border-slate-800 p-1 rounded-xl shadow-inner">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Executive Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'chat'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>AI Chat & Simulator</span>
          </button>

          <button
            onClick={() => setActiveTab('debt')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'debt'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Data Debt (31)</span>
          </button>

          <button
            onClick={() => setActiveTab('architecture')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'architecture'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Architecture & Privacy</span>
          </button>

          <button
            onClick={() => setActiveTab('monday')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'monday'
                ? 'bg-[#0073ea] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Link2 className="w-3.5 h-3.5 text-[#00ca72]" />
            <span>Monday.com Hub</span>
          </button>
        </nav>

        {/* Live Status Indicators & Actions */}
        <div className="flex items-center space-x-2">
          {/* Privacy Pill */}
          <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-[11px] text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono font-medium">Zero PII Leaked</span>
          </div>

          {/* NVIDIA NIM Pill */}
          <div className="hidden xl:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/40 border border-indigo-800/40 text-[11px] text-indigo-300">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            <span className="font-mono">NVIDIA NIM: Llama-3.3-70B</span>
          </div>

          {/* DuckDB Pill */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-950/30 border border-amber-800/40 text-[11px] text-amber-300">
            <Database className="w-3 h-3 text-amber-400" />
            <span className="font-mono">DuckDB Engine</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefreshData}
            disabled={isRefreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
            title="Refresh In-Memory Cache from Source Files"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span className="hidden md:inline">Sync Data</span>
          </button>
        </div>

      </div>
    </header>
  );
};
