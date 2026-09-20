import { useState, useEffect } from 'react';
import { apiUrl } from './apiConfig';
import type { MetaSource } from './types';
import { ChatInterface } from './components/ChatInterface';

export function App() {
  const [sourceMeta, setSourceMeta] = useState<MetaSource | null>(null);
  const [metaError, setMetaError] = useState<boolean>(false);

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-sky-500 selection:text-white">
      {/* Header: Product name and one source badge only */}
      <header className="h-14 border-b border-slate-800/80 bg-slate-900/50 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-semibold tracking-tight text-slate-100">
            Skylark BI
          </span>
        </div>

        <div>
          {sourceMeta ? (
            <div
              className="px-2.5 py-1 rounded border border-slate-800 bg-slate-900/80 font-mono text-[11px] text-slate-300"
              aria-label="Connected data source status"
            >
              {sourceMeta.display_badge ||
                `monday.com · synced ${sourceMeta.synced_at} · as of ${sourceMeta.as_of_date}`}
            </div>
          ) : metaError ? (
            <div
              className="px-2.5 py-1 rounded border border-rose-500/30 bg-rose-500/10 font-mono text-[11px] text-rose-300"
              aria-label="Data source unreachable"
            >
              source disconnected · offline
            </div>
          ) : (
            <div className="px-2.5 py-1 rounded border border-slate-800/60 bg-slate-900/40 font-mono text-[11px] text-slate-500">
              connecting...
            </div>
          )}
        </div>
      </header>

      {/* Main Single-Screen Content: Chat & BI Blocks */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;
