import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
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
      } catch (err) {
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
    <div className={`min-h-screen ${theme === 'light' ? 'bg-slate-50 text-slate-900' : 'bg-slate-950 text-slate-100'} flex flex-col font-sans selection:bg-sky-500 selection:text-white transition-colors duration-150`}>
      {/* Header: product name; segmented control Agent | Info; source badge + light/dark toggle */}
      <header className={`h-14 border-b ${theme === 'light' ? 'border-slate-200 bg-white' : 'border-slate-800/80 bg-slate-900/60'} px-4 sm:px-6 flex items-center justify-between transition-colors`}>
        {/* Left: Product Name */}
        <div className="flex items-center space-x-2">
          <span className={`text-sm font-semibold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-slate-100'}`}>
            Blindfold BI — Skylark Drones
          </span>
        </div>

        {/* Center: Segmented Control [ Agent | Info ] */}
        <div
          role="tablist"
          aria-label="Application tabs"
          className={`inline-flex items-center p-0.5 rounded-lg border ${
            theme === 'light'
              ? 'bg-slate-100 border-slate-200'
              : 'bg-slate-900 border-slate-800'
          }`}
        >
          <button
            type="button"
            role="tab"
            id="tab-agent"
            aria-controls="panel-agent"
            aria-selected={activeTab === 'agent'}
            onClick={() => setActiveTab('agent')}
            className={`px-3.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer ${
              activeTab === 'agent'
                ? 'bg-sky-600 text-white shadow-xs'
                : theme === 'light'
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Agent
          </button>
          <button
            type="button"
            role="tab"
            id="tab-info"
            aria-controls="panel-info"
            aria-selected={activeTab === 'info'}
            onClick={() => setActiveTab('info')}
            className={`px-3.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer ${
              activeTab === 'info'
                ? 'bg-sky-600 text-white shadow-xs'
                : theme === 'light'
                ? 'text-slate-600 hover:text-slate-900'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Info
          </button>
        </div>

        {/* Right: Source Badge + Light/Dark Toggle */}
        <div className="flex items-center space-x-3">
          {/* Source badge: status dot + source info */}
          {sourceMeta ? (
            <div
              className={`flex items-center space-x-2 px-2.5 py-1 rounded border font-mono text-[11px] ${
                theme === 'light'
                  ? 'border-slate-200 bg-slate-100 text-slate-700'
                  : 'border-slate-800 bg-slate-900/80 text-slate-300'
              }`}
              aria-label="Connected data source status"
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  sourceMeta.is_stale
                    ? 'bg-amber-400'
                    : sourceMeta.source === 'monday.com'
                    ? 'bg-emerald-400'
                    : 'bg-sky-400'
                }`}
              />
              <span>
                {sourceMeta.is_stale
                  ? `Stale snapshot · synced ${sourceMeta.synced_at} · as of ${sourceMeta.as_of_date}`
                  : sourceMeta.display_badge ||
                    `monday.com · synced ${sourceMeta.synced_at} · as of ${sourceMeta.as_of_date}`}
              </span>
            </div>
          ) : metaError ? (
            <div
              className="flex items-center space-x-2 px-2.5 py-1 rounded border border-rose-500/30 bg-rose-500/10 font-mono text-[11px] text-rose-300"
              aria-label="Data source unreachable"
            >
              <div className="w-2 h-2 rounded-full bg-rose-500" />
              <span>Not connected</span>
            </div>
          ) : (
            <div
              className={`flex items-center space-x-2 px-2.5 py-1 rounded border font-mono text-[11px] ${
                theme === 'light'
                  ? 'border-slate-200 bg-slate-100 text-slate-400'
                  : 'border-slate-800/60 bg-slate-900/40 text-slate-500'
              }`}
            >
              <div className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
              <span>connecting...</span>
            </div>
          )}

          {/* Light / Dark Mode Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className={`p-1.5 rounded-md border transition-colors cursor-pointer ${
              theme === 'light'
                ? 'border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                : 'border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Content Area: Agent & Info Tab Panes */}
      {/* Both panes remain mounted in the DOM to strictly preserve conversation state when switching tabs */}
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
