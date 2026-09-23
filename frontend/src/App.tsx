import { useState, useEffect } from 'react';
import { Sun, Moon, Database, ShieldCheck, Terminal, BookOpen } from 'lucide-react';
import { apiUrl } from './apiConfig';
import type { MetaSource } from './types';
import { ChatInterface } from './components/ChatInterface';
import { InfoTab } from './components/InfoTab';

export function App() {
  const [activeTab, setActiveTab] = useState<'agent' | 'info'>('agent');
  const [triggerQuery, setTriggerQuery] = useState<string | null>(null);
  const [sourceMeta, setSourceMeta] = useState<MetaSource | null>(null);
  const [metaError, setMetaError] = useState<boolean>(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    try {
      return (localStorage.getItem('bbi_theme') as 'dark' | 'light') || 'dark';
    } catch {
      return 'dark';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('bbi_theme', theme);
      if (theme === 'light') {
        document.documentElement.classList.add('light');
        document.documentElement.classList.remove('dark');
      } else {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      }
    } catch {
      // Ignore storage errors in private browsing
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  useEffect(() => {
    const fetchMetaSource = async () => {
      try {
        const res = await fetch(apiUrl('/api/v1/meta/source'));
        if (res.ok) {
          const data: MetaSource = await res.json();
          setSourceMeta(data);
          setMetaError(false);
        } else {
          setMetaError(true);
        }
      } catch {
        setMetaError(true);
      }
    };

    fetchMetaSource();
  }, []);

  const handleAskQueryFromInfo = (query: string) => {
    setTriggerQuery(query);
    setActiveTab('agent');
  };

  return (
    <div
      className={`min-h-screen ${
        theme === 'light'
          ? 'bg-[#f8fafc] text-slate-900'
          : 'bg-[#080c14] text-slate-100'
      } flex flex-col font-sans selection:bg-sky-600 selection:text-white transition-colors duration-150`}
    >
      {/* Hallmark Instrument Header */}
      <header
        className={`h-14 border-b ${
          theme === 'light'
            ? 'border-slate-200/90 bg-white/90'
            : 'border-slate-800/80 bg-[#0a0f1b]/90'
        } backdrop-blur-md px-4 sm:px-6 flex items-center justify-between transition-colors z-20 sticky top-0`}
      >
        {/* Left: Brand & Technical Register */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded bg-sky-950 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span
                  className={`text-sm font-semibold tracking-tight font-display ${
                    theme === 'light' ? 'text-slate-900' : 'text-slate-100'
                  }`}
                >
                  BLINDFOLD BI
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded uppercase bg-sky-950/80 border border-sky-500/30 text-sky-400 hidden sm:inline-block">
                  SKYLARK DRONES
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Segmented Workbench Control [ Agent | Info ] */}
        <div
          role="tablist"
          aria-label="Application tabs"
          className={`inline-flex items-center p-0.5 rounded-md border ${
            theme === 'light'
              ? 'bg-slate-100 border-slate-200'
              : 'bg-[#0d131f] border-slate-800'
          }`}
        >
          <button
            type="button"
            role="tab"
            id="tab-agent"
            aria-controls="panel-agent"
            aria-selected={activeTab === 'agent'}
            onClick={() => setActiveTab('agent')}
            className={`flex items-center space-x-1.5 px-3 py-1 text-xs font-mono font-medium rounded transition-all cursor-pointer ${
              activeTab === 'agent'
                ? 'bg-sky-600 text-white shadow-xs'
                : theme === 'light'
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-3 h-3" />
            <span>Agent Workbench</span>
          </button>
          <button
            type="button"
            role="tab"
            id="tab-info"
            aria-controls="panel-info"
            aria-selected={activeTab === 'info'}
            onClick={() => setActiveTab('info')}
            className={`flex items-center space-x-1.5 px-3 py-1 text-xs font-mono font-medium rounded transition-all cursor-pointer ${
              activeTab === 'info'
                ? 'bg-sky-600 text-white shadow-xs'
                : theme === 'light'
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="w-3 h-3" />
            <span>Data Contracts</span>
          </button>
        </div>

        {/* Right: Live Data Source Telemetry & Theme Toggle */}
        <div className="flex items-center space-x-2.5">
          {sourceMeta ? (
            <div
              className={`flex items-center space-x-2 px-2.5 py-1 rounded border font-mono text-[11px] tabular-nums ${
                theme === 'light'
                  ? 'border-slate-200 bg-slate-100 text-slate-700'
                  : 'border-slate-800 bg-[#0d131f] text-slate-300'
              }`}
              title={`Deals: ${sourceMeta.deals_count} · Work Orders: ${sourceMeta.work_orders_count} · Synced: ${sourceMeta.synced_at}`}
              aria-label="Connected data source status"
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  sourceMeta.is_stale
                    ? 'bg-amber-400'
                    : sourceMeta.source === 'monday.com'
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'
                    : 'bg-sky-400'
                }`}
              />
              <span className="hidden md:inline">
                {sourceMeta.source === 'monday.com' ? 'LIVE MONDAY.COM' : 'FIXTURE'}
              </span>
              <span className="text-slate-500 hidden lg:inline">·</span>
              <span className="hidden lg:inline text-slate-400">
                {sourceMeta.deals_count} deals · {sourceMeta.work_orders_count} WOs
              </span>
              <span className="text-slate-500 hidden xl:inline">·</span>
              <span className="hidden xl:inline text-slate-500">
                {sourceMeta.as_of_date}
              </span>
            </div>
          ) : metaError ? (
            <div
              className="flex items-center space-x-2 px-2.5 py-1 rounded border border-rose-500/30 bg-rose-500/10 font-mono text-[11px] text-rose-300"
              aria-label="Data source unreachable"
            >
              <div className="w-2 h-2 rounded-full bg-rose-500" />
              <span>Offline</span>
            </div>
          ) : (
            <div
              className={`flex items-center space-x-2 px-2.5 py-1 rounded border font-mono text-[11px] ${
                theme === 'light'
                  ? 'border-slate-200 bg-slate-100 text-slate-400'
                  : 'border-slate-800 bg-[#0d131f] text-slate-500'
              }`}
            >
              <Database className="w-3 h-3 text-slate-500 animate-pulse" />
              <span>connecting...</span>
            </div>
          )}

          {/* Light / Dark Mode Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className={`p-1.5 rounded border transition-colors cursor-pointer ${
              theme === 'light'
                ? 'border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                : 'border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>
        </div>
      </header>

      {/* Main Content Area: Agent & Info Tab Panes */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <div
          id="panel-agent"
          role="tabpanel"
          aria-labelledby="tab-agent"
          className={`flex-1 flex flex-col h-full ${activeTab === 'agent' ? 'block' : 'hidden'}`}
        >
          <ChatInterface
            triggerQuery={triggerQuery}
            onQueryTriggered={() => setTriggerQuery(null)}
          />
        </div>

        <div
          id="panel-info"
          role="tabpanel"
          aria-labelledby="tab-info"
          className={`flex-1 flex flex-col h-full overflow-y-auto ${activeTab === 'info' ? 'block' : 'hidden'}`}
        >
          <InfoTab onAskQuery={handleAskQueryFromInfo} />
        </div>
      </main>
    </div>
  );
}

export default App;
