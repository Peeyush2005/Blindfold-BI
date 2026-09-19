import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { ExecutiveDashboard } from './components/ExecutiveDashboard';
import { ChatInterface } from './components/ChatInterface';
import { DataDebtCenter } from './components/DataDebtCenter';
import { ArchitectureView } from './components/ArchitectureView';
import { MondayIntegrationView } from './components/MondayIntegrationView';
import { apiUrl } from './apiConfig';
import type { DashboardOverview } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat' | 'debt' | 'architecture' | 'monday'>('dashboard');
  const [dashboardData, setDashboardData] = useState<DashboardOverview | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [chatInitialQuery, setChatInitialQuery] = useState<string | undefined>(undefined);

  const fetchDashboardData = async () => {
    setLoadingDashboard(true);
    try {
      const res = await fetch(apiUrl('/api/dashboard'));
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
      } else {
        console.error('Failed to load dashboard:', res.status);
      }
    } catch (err) {
      console.error('Error loading dashboard:', err);
    } finally {
      setLoadingDashboard(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRefreshData = async () => {
    setIsRefreshing(true);
    try {
      const refreshRes = await fetch(apiUrl('/api/data/refresh'), { method: 'POST' });
      if (refreshRes.ok) {
        await fetchDashboardData();
      }
    } catch (err) {
      console.error('Failed to refresh data cache:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAskMetric = (metricQuestion: string) => {
    setChatInitialQuery(metricQuestion);
    setActiveTab('chat');
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col selection:bg-cyan-500 selection:text-white">
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefreshData={handleRefreshData}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {activeTab === 'dashboard' && (
          <ExecutiveDashboard
            data={dashboardData}
            loading={loadingDashboard}
            onNavigateToDebt={() => setActiveTab('debt')}
            onAskMetric={handleAskMetric}
          />
        )}

        {activeTab === 'chat' && (
          <ChatInterface
            initialQuery={chatInitialQuery}
            onClearInitialQuery={() => setChatInitialQuery(undefined)}
          />
        )}

        {activeTab === 'debt' && <DataDebtCenter />}

        {activeTab === 'architecture' && <ArchitectureView />}

        {activeTab === 'monday' && <MondayIntegrationView />}
      </main>

      {/* Persistent Footer */}
      <footer className="mt-auto border-t border-slate-800/80 bg-slate-950/80 py-4 px-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            <span className="font-mono text-slate-400">
              Blindfold BI • Skylark Drones Enterprise Intelligence
            </span>
          </div>
          <div className="flex items-center space-x-4 text-[11px] font-mono">
            <span>Zero PII Leakage</span>
            <span>•</span>
            <span>DuckDB Deterministic Engine</span>
            <span>•</span>
            <span>NVIDIA NIM Llama-3.3-70B</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
