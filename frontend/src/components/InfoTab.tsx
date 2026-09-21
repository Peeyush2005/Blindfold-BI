import React, { useState, useEffect } from 'react';
import {
  Database,
  ShieldCheck,
  HelpCircle,
  ExternalLink,
  AlertTriangle,
  ArrowRight,
  RotateCcw,
  BookOpen,
  Terminal,
  Layers,
  AlertCircle,
} from 'lucide-react';
import { apiUrl } from '../apiConfig';
import type {
  MetaSource,
  MetaQuality,
  MetaContract,
  ToolCatalogItem,
  ReadyzStatus,
} from '../types';

interface InfoTabProps {
  onAskQuery: (query: string) => void;
}

interface HealthzStatus {
  status: string;
  app: string;
  version: string;
  timestamp: number;
}

export const InfoTab: React.FC<InfoTabProps> = ({ onAskQuery }) => {
  const [source, setSource] = useState<MetaSource | null>(null);
  const [quality, setQuality] = useState<MetaQuality | null>(null);
  const [contract, setContract] = useState<MetaContract | null>(null);
  const [tools, setTools] = useState<ToolCatalogItem[]>([]);
  const [readyz, setReadyz] = useState<ReadyzStatus | null>(null);
  const [healthz, setHealthz] = useState<HealthzStatus | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadAllMetadata = async () => {
    setIsLoading(true);
    setFetchError(null);

    try {
      const [sourceRes, qualityRes, contractRes, toolsRes, readyzRes, healthzRes] =
        await Promise.all([
          fetch(apiUrl('/api/v1/meta/source')),
          fetch(apiUrl('/api/v1/meta/quality')),
          fetch(apiUrl('/api/v1/meta/contract')),
          fetch(apiUrl('/api/v1/tools'), {
            headers: { 'X-Blindfold-UI': 'web-client' },
          }),
          fetch(apiUrl('/readyz')),
          fetch(apiUrl('/healthz')),
        ]);

      if (!sourceRes.ok || !qualityRes.ok || !contractRes.ok || !toolsRes.ok) {
        throw new Error(
          `Metadata fetch failed: HTTP ${sourceRes.status} / ${qualityRes.status} / ${contractRes.status}`
        );
      }

      const [sourceData, qualityData, contractData, toolsData] = await Promise.all([
        sourceRes.json(),
        qualityRes.json(),
        contractRes.json(),
        toolsRes.json(),
      ]);

      setSource(sourceData);
      setQuality(qualityData);
      setContract(contractData);
      setTools(toolsData);

      if (readyzRes.ok) {
        const readyzData = await readyzRes.json();
        setReadyz(readyzData);
      }
      if (healthzRes.ok) {
        const healthzData = await healthzRes.json();
        setHealthz(healthzData);
      }
    } catch (err: any) {
      console.error('Failed to load InfoTab metadata:', err);
      setFetchError(
        err.message || 'Unable to connect to backend analytical metadata endpoints.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllMetadata();
  }, []);

  // Group tools by domain for Section 4
  const toolsByDomain = React.useMemo(() => {
    const grouped: Record<string, ToolCatalogItem[]> = {};
    for (const t of tools) {
      const domain = t.domain || 'General';
      if (!grouped[domain]) grouped[domain] = [];
      grouped[domain].push(t);
    }
    return grouped;
  }, [tools]);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto w-full px-4 py-8 space-y-6 text-slate-300">
        <div className="h-6 w-48 bg-slate-800 animate-pulse rounded" />
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="p-5 rounded-md border border-slate-800 bg-slate-900/40 space-y-3"
            >
              <div className="h-4 w-36 bg-slate-800 animate-pulse rounded" />
              <div className="h-3 w-3/4 bg-slate-800/60 animate-pulse rounded" />
              <div className="h-3 w-1/2 bg-slate-800/60 animate-pulse rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="max-w-4xl mx-auto w-full px-4 py-12">
        <div
          role="alert"
          className="p-5 rounded-md border border-rose-500/40 bg-rose-500/10 text-rose-200 space-y-3"
        >
          <div className="flex items-center space-x-2 font-medium text-sm">
            <AlertCircle className="w-5 h-5 text-rose-400" />
            <span>Backend Analytical Endpoints Unreachable</span>
          </div>
          <p className="text-xs text-rose-300 leading-relaxed">{fetchError}</p>
          <div className="pt-2">
            <button
              type="button"
              onClick={loadAllMetadata}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-rose-900/40 hover:bg-rose-900/60 border border-rose-700/50 text-xs font-medium text-rose-200 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto w-full px-4 py-8 space-y-10 text-slate-200 pb-20">
      {/* ------------------------------------------------------------------- */}
      {/* Section 1: Data Source & Freshness */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <Database className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            1. Data Source & Freshness
          </h2>
        </div>

        {source && (
          <div className="p-4 rounded-md border border-slate-800 bg-slate-900/40 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              <div className="p-3 rounded bg-slate-900/80 border border-slate-800/80">
                <div className="text-[11px] font-mono text-slate-400">Data Source Mode</div>
                <div className="text-sm font-medium text-slate-200 mt-1 capitalize flex items-center space-x-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      source.source === 'monday.com'
                        ? 'bg-emerald-400'
                        : source.is_stale
                        ? 'bg-amber-400'
                        : 'bg-sky-400'
                    }`}
                  />
                  <span>{source.source}</span>
                  {source.is_stale && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Stale Snapshot
                    </span>
                  )}
                </div>
              </div>

              <div className="p-3 rounded bg-slate-900/80 border border-slate-800/80">
                <div className="text-[11px] font-mono text-slate-400">As-of Date & Sync</div>
                <div className="text-sm font-medium text-slate-200 mt-1 font-mono">
                  {source.as_of_date} · {source.synced_at}
                </div>
              </div>

              <div className="p-3 rounded bg-slate-900/80 border border-slate-800/80">
                <div className="text-[11px] font-mono text-slate-400">Snapshot Age</div>
                <div className="text-sm font-medium text-slate-200 mt-1 font-mono">
                  {source.snapshot_age_seconds !== undefined
                    ? `${Math.floor(source.snapshot_age_seconds / 60)}m ${
                        source.snapshot_age_seconds % 60
                      }s ago`
                    : 'Realtime'}
                </div>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Connected Boards:</span>
                <span className="font-mono text-slate-200">
                  {source.board_names?.join(', ') || 'Deal funnel, Work_Order_Tracker'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Item Counts Loaded:</span>
                <span className="font-mono text-slate-200">
                  {source.deals_count} Deals · {source.work_orders_count} Work Orders
                </span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="text-slate-400">Refresh Policy:</span>
                <span className="text-slate-300 font-mono text-[11px]">
                  {source.refresh_policy || 'Auto-sync every 10 minutes (single-flight background refresh)'}
                </span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* Section 2: Data Health Summary */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            2. Data Health Summary & Hygiene Ledger
          </h2>
        </div>

        {quality && (
          <div className="space-y-4">
            {/* Top Stat Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 rounded-md border border-slate-800 bg-slate-900/40">
                <div className="text-[11px] font-mono text-slate-400">Rows Loaded / Used</div>
                <div className="text-xs font-mono font-medium text-slate-200 mt-1">
                  Deals: {quality.rows_loaded?.deals} / {quality.rows_used?.deals}
                </div>
                <div className="text-xs font-mono font-medium text-slate-200">
                  Orders: {quality.rows_loaded?.work_orders} / {quality.rows_used?.work_orders}
                </div>
              </div>

              <div className="p-3 rounded-md border border-slate-800 bg-slate-900/40">
                <div className="text-[11px] font-mono text-slate-400">Duplicates Removed</div>
                <div className="text-sm font-mono font-medium text-slate-200 mt-1">
                  {quality.duplicates_removed} records
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">Deduplicated in memory</div>
              </div>

              <div className="p-3 rounded-md border border-slate-800 bg-slate-900/40">
                <div className="text-[11px] font-mono text-slate-400">Null Deal Values</div>
                <div className="text-sm font-mono font-medium text-amber-400 mt-1">
                  {quality.share_of_deals_with_no_value}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">Coverage caveat flagged</div>
              </div>

              <div className="p-3 rounded-md border border-slate-800 bg-slate-900/40">
                <div className="text-[11px] font-mono text-slate-400">Total Anomalies</div>
                <div className="text-sm font-mono font-medium text-slate-200 mt-1">
                  {quality.total_anomalies} infractions
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">Across DQ001–DQ016</div>
              </div>
            </div>

            {/* Empty Columns Pill List */}
            {quality.empty_columns && quality.empty_columns.length > 0 && (
              <div className="p-3 rounded-md border border-slate-800 bg-slate-900/30 text-xs">
                <span className="text-slate-400 font-medium mr-2">Empty Columns Ignored:</span>
                <div className="inline-flex flex-wrap gap-1.5 mt-1">
                  {quality.empty_columns.map((col, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-300 border border-slate-700/60"
                    >
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* DQ Codes Table with "Ask the agent" Link */}
            <div className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/40">
              <div className="px-3.5 py-2.5 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs font-medium text-slate-300">
                <span>Active Data Quality Checks</span>
                <span className="text-[11px] font-mono text-slate-500">
                  {quality.dq_codes?.length || 0} rules checked
                </span>
              </div>

              <div className="divide-y divide-slate-800/60">
                {quality.dq_codes?.map((dq) => (
                  <div
                    key={dq.code}
                    className="p-3 hover:bg-slate-900/60 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs"
                  >
                    <div className="space-y-1 max-w-xl">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-sky-400">{dq.code}</span>
                        <span className="font-medium text-slate-200">{dq.name}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded font-mono uppercase ${
                            dq.severity === 'high'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : dq.severity === 'medium'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {dq.severity}
                        </span>
                        <span className="font-mono text-slate-400 text-[11px]">
                          ({dq.count} records)
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 leading-relaxed">
                        {dq.why_it_matters}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => onAskQuery(dq.example_query || `Tell me about ${dq.name}`)}
                      className="inline-flex items-center space-x-1 self-start sm:self-center px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-300 hover:text-white border border-slate-700 transition-colors text-[11px] font-medium shrink-0 cursor-pointer"
                    >
                      <span>Ask the agent</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* Section 3: Definitions & Assumptions */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <BookOpen className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            3. Definitions, Contracts & Assumptions
          </h2>
        </div>

        {contract && (
          <div className="space-y-4 text-xs">
            {/* Metric Governance Table */}
            <div className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/40">
              <div className="px-3.5 py-2.5 border-b border-slate-800 bg-slate-900/80 font-medium text-slate-300">
                Authoritative Metric Definitions (Contracts)
              </div>
              <div className="divide-y divide-slate-800/60">
                {contract.metric_definitions?.map((m) => (
                  <div key={m.name} className="p-3 space-y-1">
                    <div className="flex items-center justify-between flex-wrap gap-1">
                      <span className="font-medium text-slate-200">{m.display_name}</span>
                      <span className="font-mono text-[11px] text-sky-400">{m.basis}</span>
                    </div>
                    <div className="text-slate-400 text-[11px]">{m.description}</div>
                    <div className="font-mono text-[11px] text-slate-500 bg-slate-950/80 px-2 py-0.5 rounded inline-block mt-0.5">
                      {m.formula}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Context & Policy Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Energy Sector Group Card */}
              <div className="p-3.5 rounded-md border border-slate-800 bg-slate-900/40 space-y-2">
                <div className="font-medium text-slate-200 flex items-center justify-between">
                  <span>Energy Sector Cluster</span>
                  <span className="font-mono text-[11px] text-slate-400">Canonical Definition</span>
                </div>
                <div className="text-slate-400 text-[11px] leading-relaxed">
                  {contract.energy_sector_group?.description}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {contract.energy_sector_group?.sectors.map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-emerald-400 border border-slate-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Fiscal Year Policy Card */}
              <div className="p-3.5 rounded-md border border-slate-800 bg-slate-900/40 space-y-2">
                <div className="font-medium text-slate-200 flex items-center justify-between">
                  <span>Fiscal Year Policy</span>
                  <span className="font-mono text-[11px] text-slate-400">Indian FY (April Start)</span>
                </div>
                <div className="space-y-1 text-[11px] font-mono text-slate-300">
                  <div>Current FY: {contract.fiscal_year_policy?.current_fy}</div>
                  <div>Current Quarter: {contract.fiscal_year_policy?.current_quarter} ({contract.fiscal_year_policy?.quarter_range})</div>
                  <div>As-of Anchor Date: {contract.fiscal_year_policy?.as_of_date}</div>
                </div>
              </div>
            </div>

            {/* Probability Weights Grid */}
            <div className="p-3.5 rounded-md border border-slate-800 bg-slate-900/40 space-y-2">
              <div className="font-medium text-slate-200">Probability Conversion Weights</div>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {contract.probability_weights &&
                  Object.entries(contract.probability_weights).map(([stage, weight]) => (
                    <div
                      key={stage}
                      className="p-2 rounded bg-slate-900/80 border border-slate-800 text-center"
                    >
                      <div className="text-[11px] text-slate-400">{stage}</div>
                      <div className="font-mono font-semibold text-slate-200 mt-0.5">
                        {(weight * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            {/* Cross-Board Linkage Notice */}
            <div className="p-3 rounded-md border border-amber-500/20 bg-amber-500/5 text-amber-200/90 text-xs flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-300">Cross-Board Join Policy (DQ015): </span>
                <span>{contract.cross_board_join_policy}</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* Section 4: What You Can Ask (Tool Catalog) */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <HelpCircle className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            4. What You Can Ask (Deterministic Capabilities)
          </h2>
        </div>

        <div className="space-y-4">
          {Object.entries(toolsByDomain).map(([domain, domainTools]) => (
            <div
              key={domain}
              className="p-4 rounded-md border border-slate-800 bg-slate-900/40 space-y-3"
            >
              <div className="text-xs font-semibold text-sky-400 uppercase tracking-wider flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5" />
                <span>{domain} Domain ({domainTools.length} tools)</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {domainTools.map((tool) => (
                  <div
                    key={tool.name}
                    className="p-3 rounded bg-slate-900/80 border border-slate-800/80 space-y-2 flex flex-col justify-between"
                  >
                    <div>
                      <div className="font-mono text-xs font-medium text-slate-200">
                        {tool.name}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        {tool.description}
                      </div>
                    </div>

                    {/* 2 Clickable Example Chips */}
                    {tool.examples && tool.examples.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/60 space-y-1">
                        <div className="text-[10px] text-slate-500 font-mono">Example Queries:</div>
                        <div className="flex flex-col gap-1">
                          {tool.examples.slice(0, 2).map((example, eIdx) => (
                            <button
                              key={eIdx}
                              type="button"
                              onClick={() => onAskQuery(example)}
                              className="text-left px-2 py-1 rounded bg-slate-800/60 hover:bg-slate-800 text-[11px] text-slate-300 hover:text-white border border-slate-700/60 transition-colors truncate cursor-pointer flex items-center justify-between group"
                            >
                              <span className="truncate">{example}</span>
                              <ArrowRight className="w-3 h-3 text-slate-500 group-hover:text-sky-400 shrink-0 ml-1" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* Section 5: Privacy & Limits */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            5. Privacy Guarantees & Operational Limits
          </h2>
        </div>

        <div className="p-4 rounded-md border border-slate-800 bg-slate-900/40 space-y-3 text-xs leading-relaxed text-slate-300">
          <p>
            <strong className="text-slate-100">1. Strict Read-Only Access: </strong>
            Blindfold BI operates with zero write or mutation permissions on monday.com boards,
            preventing unintended state alterations via an enforced in-process mutation guard.
          </p>
          <p>
            <strong className="text-slate-100">2. Surrogate Tokenization: </strong>
            All client tokens, account owners, and deal names are pseudonymized using
            session-scoped HMAC-SHA256 salts before reaching language models, preventing sensitive
            identity disclosure.
          </p>
          <p>
            <strong className="text-slate-100">3. Blindfold Execution: </strong>
            The language model never inspects raw data rows or computes mental arithmetic; it only
            narrates verified facts deterministically produced by local DuckDB SQL execution.
          </p>

          <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400">
            <div>
              LLM Status:{' '}
              <span
                className={`font-semibold ${
                  readyz?.llm_configured ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {readyz?.llm_configured ? 'Configured & Active' : 'Fallback Dynamic Templates'}
              </span>
            </div>
            <div>
              Key Store:{' '}
              <span className="text-slate-300 font-semibold">{readyz?.key_store || 'Active'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* Section 6: API Documentation & Diagnostic Endpoints */}
      {/* ------------------------------------------------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <Terminal className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight uppercase">
            6. Programmatic API & Diagnostics
          </h2>
        </div>

        <div className="p-4 rounded-md border border-slate-800 bg-slate-900/40 space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 rounded bg-slate-900/80 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/80 transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-slate-200">OpenAPI Interactive Swagger</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Explore /docs with API Key Auth</div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-sky-400" />
            </a>

            <a
              href="/mcp"
              target="_blank"
              rel="noopener noreferrer"
              className="p-3 rounded bg-slate-900/80 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/80 transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-slate-200">Model Context Protocol (MCP)</div>
                <div className="text-[11px] text-slate-400 mt-0.5">FastMCP analytical tool bridge</div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-sky-400" />
            </a>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60 font-mono text-[11px]">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-400">/healthz:</span>
              <span className="text-slate-200">{healthz?.status || 'ok'} (v{healthz?.version || '1.0.0'})</span>
            </div>

            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-400">/readyz:</span>
              <span className="text-slate-200">{readyz?.status || 'ready'}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
