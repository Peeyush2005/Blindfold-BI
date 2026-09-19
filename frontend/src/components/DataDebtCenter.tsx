import React, { useState, useEffect } from 'react';
import {
  AlertTriangle, Download, Filter, Search, RefreshCw
} from 'lucide-react';
import type { DataDebtItem } from '../types';

export const DataDebtCenter: React.FC = () => {
  const [items, setItems] = useState<DataDebtItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  useEffect(() => {
    fetchDataDebt();
  }, []);

  const fetchDataDebt = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/data-debt');
      if (res.ok) {
        const data = await res.json();
        const records = Array.isArray(data) ? data : (data.records || []);
        setItems(records);
      }
    } catch (err) {
      console.error('Failed to load data debt', err);
    } finally {
      setLoading(false);
    }
  };

  const categories = Array.from(new Set(items.map(i => i.issue_category))).filter(Boolean);

  const filteredItems = items.filter(item => {
    const matchesSearch =
      item.entity_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.owner.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity = selectedSeverity === 'ALL' || (item.severity || '').toUpperCase() === selectedSeverity;
    const matchesCategory = selectedCategory === 'ALL' || item.issue_category === selectedCategory;

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  const highCount = items.filter(i => (i.severity || '').toUpperCase() === 'HIGH').length;
  const medCount = items.filter(i => (i.severity || '').toUpperCase() === 'MEDIUM').length;
  const lowCount = items.filter(i => (i.severity || '').toUpperCase() === 'LOW').length;

  return (
    <div className="space-y-6 pb-12">

      {/* Header & Export Action */}
      <div className="bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-950 border border-amber-900/40 rounded-2xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-amber-950/80 border border-amber-700/60 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight m-0">
                Data Hygiene & CRM Debt Audit Center
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Automated detection of unbilled completions, missing dates, and deal conversion leakage
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <a
            href="/api/data-debt/export"
            download="skylark_data_debt_report.csv"
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV Audit Report</span>
          </a>

          <button
            onClick={fetchDataDebt}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh Audit Scanner"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Severity Summary Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setSelectedSeverity('ALL')}
          className={`bg-slate-900/80 border p-4 rounded-2xl cursor-pointer transition ${
            selectedSeverity === 'ALL' ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-slate-800'
          }`}
        >
          <span className="text-xs text-slate-400 font-medium">Total Anomalies</span>
          <div className="text-2xl font-black text-white mt-1 font-mono">{items.length}</div>
          <span className="text-[10px] text-slate-500">Across 342 deals & 175 WOs</span>
        </div>

        <div
          onClick={() => setSelectedSeverity('HIGH')}
          className={`bg-slate-900/80 border p-4 rounded-2xl cursor-pointer transition ${
            selectedSeverity === 'HIGH' ? 'border-rose-500 ring-2 ring-rose-500/20' : 'border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-rose-400 font-medium">High Severity</span>
            <span className="h-2 w-2 rounded-full bg-rose-500" />
          </div>
          <div className="text-2xl font-black text-rose-300 mt-1 font-mono">{highCount}</div>
          <span className="text-[10px] text-slate-500">Immediate revenue risk</span>
        </div>

        <div
          onClick={() => setSelectedSeverity('MEDIUM')}
          className={`bg-slate-900/80 border p-4 rounded-2xl cursor-pointer transition ${
            selectedSeverity === 'MEDIUM' ? 'border-amber-500 ring-2 ring-amber-500/20' : 'border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-400 font-medium">Medium Severity</span>
            <span className="h-2 w-2 rounded-full bg-amber-500" />
          </div>
          <div className="text-2xl font-black text-amber-300 mt-1 font-mono">{medCount}</div>
          <span className="text-[10px] text-slate-500">Audit & milestone delays</span>
        </div>

        <div
          onClick={() => setSelectedSeverity('LOW')}
          className={`bg-slate-900/80 border p-4 rounded-2xl cursor-pointer transition ${
            selectedSeverity === 'LOW' ? 'border-sky-500 ring-2 ring-sky-500/20' : 'border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-sky-400 font-medium">Low Severity</span>
            <span className="h-2 w-2 rounded-full bg-sky-500" />
          </div>
          <div className="text-2xl font-black text-sky-300 mt-1 font-mono">{lowCount}</div>
          <span className="text-[10px] text-slate-500">Metadata hygiene</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search entity, description, owner..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none"
          >
            <option value="ALL">All Categories</option>
            {categories.map((cat, i) => (
              <option key={i} value={cat}>{cat}</option>
            ))}
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Anomaly Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase">
                <th className="py-3 px-4">Record ID / Entity</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Issue Category</th>
                <th className="py-3 px-4">Owner & Sector</th>
                <th className="py-3 px-4">Diagnosis & Description</th>
                <th className="py-3 px-4">Recommended Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-mono font-semibold text-cyan-300">{item.id}</div>
                    <div className="text-slate-300 text-[11px] mt-0.5 truncate max-w-[150px]" title={item.entity_name}>
                      {item.entity_name}
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                      (item.severity || '').toUpperCase() === 'HIGH' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                      (item.severity || '').toUpperCase() === 'MEDIUM' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                      'bg-sky-950 text-sky-300 border border-sky-800'
                    }`}>
                      {item.severity}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-slate-300 font-medium">
                    {item.issue_category}
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="text-slate-200">{item.owner}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{item.sector}</div>
                  </td>

                  <td className="py-3.5 px-4 text-slate-300 max-w-xs leading-relaxed">
                    {item.description}
                  </td>

                  <td className="py-3.5 px-4 text-indigo-300 max-w-xs text-[11px] leading-relaxed">
                    {item.recommended_action}
                  </td>
                </tr>
              ))}

              {filteredItems.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500">
                    No data debt items matching the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
