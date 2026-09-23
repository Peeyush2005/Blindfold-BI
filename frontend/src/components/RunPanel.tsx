import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  MinusCircle,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  ShieldCheck,
  Cpu,
  Layers,
  Database,
  Lock,
  FileCheck,
  Activity,
  ArrowRight,
  Terminal,
  Clock,
  Sparkles,
} from 'lucide-react';
import type { StageState, ToolEventData } from '../types';

interface RunPanelProps {
  stages: StageState[];
  tools: ToolEventData[];
  totalMs?: number;
  isCompleted: boolean;
  isError?: boolean;
  degraded?: boolean;
  onReplay?: () => void;
  isReplaying?: boolean;
  model?: string;
  llmCalled?: boolean;
  narrationSource?: 'llm' | 'llm_repaired' | 'template';
  templateReason?: string | null;
}

interface StageMetaInfo {
  index: string;
  name: string;
  shortName: string;
  subtitle: string;
  guarantee: string;
  tag: string;
  icon: React.ElementType;
}

const STAGE_CONFIG: Record<string, StageMetaInfo> = {
  understand: {
    index: '01',
    name: 'Understand & Scope',
    shortName: 'Scope',
    subtitle: 'Intent parsing, temporal window resolution & entity tokenization',
    guarantee: 'Zero PII Egress: Client codes and deal names converted to session HMAC-SHA256 surrogates',
    tag: 'PRIVACY GATEWAY',
    icon: Lock,
  },
  plan: {
    index: '02',
    name: 'Tool Planning',
    shortName: 'Plan',
    subtitle: 'Decentralized analytical tool selection & parameter generation',
    guarantee: 'Typed Contract: Model selects from pre-registered analytical tools; direct SQL access is prohibited',
    tag: 'REGISTRY',
    icon: Layers,
  },
  fetch: {
    index: '03',
    name: 'monday.com Snapshot',
    shortName: 'Fetch',
    subtitle: 'Read-only GraphQL v2 retrieval & snapshot cache validation',
    guarantee: 'Read-only Guard: Zero mutations permitted. Deals (332) & Work Orders (176) boards synced',
    tag: 'GRAPHQL V2',
    icon: Database,
  },
  normalize: {
    index: '04',
    name: 'Normalize & DQ Audit',
    shortName: 'Normalize',
    subtitle: 'Schema normalization & DQ ledger execution across rules DQ001-DQ016',
    guarantee: 'Data Hygiene: Header alignment, duplicate elimination, null quarantine, and GST reconciliation',
    tag: 'DQ LEDGER',
    icon: FileCheck,
  },
  compute: {
    index: '05',
    name: 'Deterministic Compute',
    shortName: 'Compute',
    subtitle: 'In-memory columnar SQL execution in DuckDB',
    guarantee: 'Zero LLM Math: 100% of arithmetic, pipeline weighting, and AR aging computed deterministically',
    tag: 'DUCKDB SQL',
    icon: Cpu,
  },
  narrate: {
    index: '06',
    name: 'Structured Synthesis',
    shortName: 'Narrate',
    subtitle: 'Prose synthesis with numbers-by-reference citations ([[F1]], [[F2]])',
    guarantee: 'Referential Truth: Model generates commentary with citation slots mapped to verified facts',
    tag: 'NUMBERS BY REF',
    icon: Sparkles,
  },
  verify: {
    index: '07',
    name: 'AST Reconciliation',
    shortName: 'Verify',
    subtitle: 'Abstract syntax tree verification of numeric claims against DuckDB output',
    guarantee: 'Hallucination Guard: Every numeric claim is reconciled against the computed dataset',
    tag: 'AST VERIFIER',
    icon: ShieldCheck,
  },
  finalize: {
    index: '08',
    name: 'Token Rehydration',
    shortName: 'Finalize',
    subtitle: 'HMAC surrogate restoration & cryptographic trust receipt issuance',
    guarantee: 'Cryptographic Trust: Secure entity rehydration & audit receipt with execution timings',
    tag: 'TRUST RECEIPT',
    icon: Activity,
  },
};

export const RunPanel: React.FC<RunPanelProps> = ({
  stages,
  tools,
  totalMs,
  isCompleted,
  isError = false,
  degraded = false,
  onReplay,
  isReplaying = false,
  model,
  llmCalled,
  narrationSource,
  templateReason,
}) => {
  // Auto-expand during live execution, collapse once complete
  const [expanded, setExpanded] = useState<boolean>(!isCompleted);
  const [selectedStageName, setSelectedStageName] = useState<string | null>(null);

  useEffect(() => {
    if (!isCompleted) {
      setExpanded(true);
    } else {
      setExpanded(false);
    }
  }, [isCompleted]);

  const totalRows = tools.reduce((acc, t) => acc + (t.rows_out || t.rows_in || 0), 0);
  const durationSec = totalMs ? (totalMs / 1000).toFixed(2) : '0.00';

  // Find active stage if running
  const activeStage = stages.find((s) => s.status === 'running');
  const completedStagesCount = stages.filter((s) => s.status === 'done').length;

  const renderStatusDot = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500" />
          </span>
        );
      case 'done':
        return <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />;
      case 'warn':
        return <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />;
      case 'error':
        return <span className="inline-block h-1.5 w-1.5 rounded-full bg-rose-500" />;
      case 'skipped':
        return <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-600" />;
      case 'queued':
      default:
        return <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-700" />;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-sky-950/80 border border-sky-500/30 text-sky-400">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
            <span>Running</span>
          </span>
        );
      case 'done':
        return (
          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-emerald-950/60 border border-emerald-500/30 text-emerald-400">
            <CheckCircle2 className="w-2.5 h-2.5" />
            <span>Verified</span>
          </span>
        );
      case 'warn':
        return (
          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-amber-950/60 border border-amber-500/30 text-amber-400">
            <AlertTriangle className="w-2.5 h-2.5" />
            <span>Degraded</span>
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-rose-950/60 border border-rose-500/30 text-rose-400">
            <XCircle className="w-2.5 h-2.5" />
            <span>Error</span>
          </span>
        );
      case 'skipped':
        return (
          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-slate-900 border border-slate-800 text-slate-500">
            <MinusCircle className="w-2.5 h-2.5" />
            <span>Skipped</span>
          </span>
        );
      case 'queued':
      default:
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-slate-900/80 border border-slate-800 text-slate-500">
            Queued
          </span>
        );
    }
  };

  return (
    <div
      className="my-3 rounded-lg border border-slate-800/90 bg-[#0a0e17] text-slate-200 overflow-hidden shadow-sm transition-all"
      aria-live="polite"
      aria-label="Analytical Pipeline Walkthrough"
    >
      {/* 1. Hallmark Instrument Telemetry Header */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#0d131f] border-b border-slate-800/80">
        <div className="flex items-center space-x-3 flex-wrap gap-y-1.5">
          {/* Main Status Pill */}
          <div className="flex items-center space-x-2">
            {!isCompleted && !isError ? (
              <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium tracking-tight bg-sky-950/80 border border-sky-500/40 text-sky-300">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                <span>
                  PIPELINE EXECUTING ({activeStage ? STAGE_CONFIG[activeStage.name]?.shortName || activeStage.name : `${completedStagesCount}/8`})
                </span>
              </span>
            ) : isError ? (
              <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium tracking-tight bg-rose-950/80 border border-rose-500/40 text-rose-300">
                <XCircle className="w-3 h-3 text-rose-400" />
                <span>EXECUTION HALTED</span>
              </span>
            ) : degraded ? (
              <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium tracking-tight bg-amber-950/80 border border-amber-500/40 text-amber-300">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                <span>DEGRADED EXECUTION</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium tracking-tight bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>8-STAGE AUDIT VERIFIED</span>
              </span>
            )}
          </div>

          {/* Precision Latency & Row Counts */}
          <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400 tabular-nums">
            <span className="flex items-center space-x-1">
              <Clock className="w-3 h-3 text-slate-500" />
              <span>{durationSec}s</span>
            </span>
            <span className="text-slate-600">·</span>
            <span>{tools.length} {tools.length === 1 ? 'tool' : 'tools'}</span>
            <span className="text-slate-600">·</span>
            <span>{totalRows} rows</span>
          </div>

          {/* Narration Provenance Badge */}
          {narrationSource === 'llm' && (
            <span
              className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              title="Verified natural language commentary generated by LLM and validated by AST verifier"
            >
              <Sparkles className="w-2.5 h-2.5" />
              <span>LLM VERIFIED</span>
            </span>
          )}
          {narrationSource === 'llm_repaired' && (
            <span
              className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"
              title="Narration repaired by LLM after initial verifier rejection"
            >
              <AlertTriangle className="w-2.5 h-2.5" />
              <span>LLM REPAIRED</span>
            </span>
          )}
          {narrationSource === 'template' && (
            <span
              className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20"
              title={`Deterministic template: ${templateReason || 'fallback'}`}
            >
              <Terminal className="w-2.5 h-2.5" />
              <span>DETERMINISTIC FALLBACK{templateReason ? ` (${templateReason})` : ''}</span>
            </span>
          )}

          {/* LLM Invocation Status */}
          {llmCalled !== undefined && (
            <span
              className={`hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                llmCalled
                  ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
              title={llmCalled ? 'LLM called for narration' : 'No LLM called (deterministic)'}
            >
              llm: {llmCalled ? 'active' : 'off'}
            </span>
          )}

          {/* Model Tag */}
          {model && (
            <span
              className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800 truncate max-w-[140px]"
              title={`Inference Model: ${model}`}
            >
              {model.split('/').pop() || model}
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Replay Button */}
          {isCompleted && onReplay && (
            <button
              type="button"
              onClick={onReplay}
              disabled={isReplaying}
              className="flex items-center space-x-1 px-2.5 py-1 rounded text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 transition-colors text-[11px] font-mono cursor-pointer"
              title="Re-run the 8-stage pipeline simulation"
              aria-label="Replay analytical pipeline walkthrough"
            >
              <RotateCcw className={`w-3 h-3 text-sky-400 ${isReplaying ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Replay</span>
            </button>
          )}

          {/* Expand / Collapse Button */}
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center space-x-1 px-2 py-1 rounded text-slate-400 hover:text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors text-[11px] font-mono cursor-pointer"
            aria-label={expanded ? 'Collapse pipeline walkthrough' : 'Expand pipeline walkthrough'}
          >
            <span>{expanded ? 'Hide' : 'Inspect'}</span>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 2. Horizontal Ribbon Stepper Track (Visible when collapsed or expanded) */}
      <div className="px-3 py-2 bg-[#080c14] border-b border-slate-800/60 overflow-x-auto">
        <div className="flex items-center justify-between min-w-[560px] gap-1">
          {stages.map((stage, idx) => {
            const meta = STAGE_CONFIG[stage.name] || {
              index: String(idx + 1).padStart(2, '0'),
              name: stage.name,
              shortName: stage.name,
              subtitle: '',
              guarantee: '',
              tag: 'STAGE',
              icon: Cpu,
            };
            const isSelected = selectedStageName === stage.name;
            const isRunning = stage.status === 'running';
            const isDone = stage.status === 'done';

            return (
              <React.Fragment key={stage.name}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedStageName(isSelected ? null : stage.name);
                    if (!expanded) setExpanded(true);
                  }}
                  className={`flex flex-col items-center p-1.5 rounded transition-all cursor-pointer text-left ${
                    isSelected
                      ? 'bg-slate-800/80 border border-sky-500/50'
                      : isRunning
                      ? 'bg-sky-950/40 border border-sky-500/30'
                      : 'hover:bg-slate-900 border border-transparent'
                  }`}
                  title={`${meta.name}: ${stage.status} (${stage.duration_ms ? stage.duration_ms.toFixed(1) + 'ms' : 'queued'})`}
                >
                  <div className="flex items-center space-x-1.5 mb-0.5">
                    <span
                      className={`text-[9px] font-mono font-medium px-1 py-0.2 rounded ${
                        isDone
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/20'
                          : isRunning
                          ? 'bg-sky-950 text-sky-400 border border-sky-500/40'
                          : 'bg-slate-900 text-slate-500'
                      }`}
                    >
                      {meta.index}
                    </span>
                    {renderStatusDot(stage.status)}
                  </div>
                  <span
                    className={`text-[10px] font-mono truncate max-w-[65px] ${
                      isSelected
                        ? 'text-sky-300 font-semibold'
                        : isRunning
                        ? 'text-sky-400 font-medium'
                        : isDone
                        ? 'text-slate-300'
                        : 'text-slate-500'
                    }`}
                  >
                    {meta.shortName}
                  </span>
                  <span className="text-[9px] font-mono text-slate-500 tabular-nums">
                    {stage.duration_ms !== undefined ? `${stage.duration_ms.toFixed(0)}ms` : '—'}
                  </span>
                </button>

                {/* Arrow connector between steps */}
                {idx < stages.length - 1 && (
                  <div className="flex items-center justify-center text-slate-700 px-0.5">
                    <ArrowRight className="w-2.5 h-2.5" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* 3. Detailed Walkthrough Accordion Body */}
      {expanded && (
        <div className="divide-y divide-slate-800/60 p-3 bg-[#0a0e17] space-y-2">
          {/* Top Note on Blindfold Architecture */}
          <div className="px-3 py-2 rounded bg-[#0d131f] border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0" />
              <span>
                <strong className="text-slate-200">Hallmark Analytical Verification:</strong> Deterministic DuckDB SQL execution, zero LLM arithmetic, and HMAC-SHA256 privacy tokenization.
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
              IN-MEMORY COLUMNAR PIPELINE
            </span>
          </div>

          {/* Stages Breakdown List */}
          <div className="space-y-1.5 pt-2">
            {stages.map((stage) => {
              const meta = STAGE_CONFIG[stage.name] || {
                index: '00',
                name: stage.name,
                shortName: stage.name,
                subtitle: 'Execution stage',
                guarantee: 'Pipeline guarantee enforced',
                tag: 'STEP',
                icon: Cpu,
              };
              const isSelected = selectedStageName === stage.name;
              const IconComponent = meta.icon;
              const duration = stage.duration_ms !== undefined ? `${stage.duration_ms.toFixed(1)}ms` : '—';

              return (
                <div
                  key={stage.name}
                  className={`rounded-md border transition-all ${
                    isSelected
                      ? 'border-sky-500/40 bg-[#0d1524]'
                      : stage.status === 'running'
                      ? 'border-sky-500/30 bg-[#0c1421]'
                      : 'border-slate-800/80 bg-[#0c101b] hover:bg-[#0f1422]'
                  }`}
                >
                  {/* Stage summary row */}
                  <div
                    onClick={() => setSelectedStageName(isSelected ? null : stage.name)}
                    className="flex items-center justify-between p-2.5 cursor-pointer select-none"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedStageName(isSelected ? null : stage.name);
                      }
                    }}
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      {/* Stage Index Pill */}
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0 font-medium">
                        S{meta.index}
                      </span>

                      {/* Icon */}
                      <div className="p-1 rounded bg-slate-900/80 border border-slate-800 shrink-0 text-slate-400">
                        <IconComponent className="w-3.5 h-3.5 text-sky-400" />
                      </div>

                      {/* Title & Subtitle */}
                      <div className="min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-slate-200 text-xs tracking-tight">
                            {meta.name}
                          </span>
                          <span className="text-[9px] font-mono uppercase px-1 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-500 hidden sm:inline-block">
                            {meta.tag}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 truncate max-w-sm sm:max-w-md">
                          {meta.subtitle}
                        </div>
                      </div>
                    </div>

                    {/* Right side: Duration + Status Badge */}
                    <div className="flex items-center space-x-2.5 shrink-0 font-mono text-[11px] tabular-nums">
                      <span className="text-slate-400">{duration}</span>
                      {renderStatusBadge(stage.status)}
                      <ChevronDown
                        className={`w-3 h-3 text-slate-500 transition-transform ${isSelected ? 'rotate-180 text-sky-400' : ''}`}
                      />
                    </div>
                  </div>

                  {/* Expanded Stage Drawer */}
                  {isSelected && (
                    <div className="px-3 pb-3 pt-1 border-t border-slate-800/60 text-xs space-y-2 bg-[#090e18]">
                      {/* Architectural Guarantee Pill */}
                      <div className="p-2 rounded bg-[#0d131f] border border-slate-800 flex items-start space-x-2 text-[11px] text-slate-300">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-emerald-400 font-mono text-[10px] uppercase block tracking-wider mb-0.5">
                            Architectural Guarantee
                          </strong>
                          <span>{meta.guarantee}</span>
                        </div>
                      </div>

                      {/* Stage Telemetry / Meta */}
                      {stage.meta && Object.keys(stage.meta).length > 0 && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-850 font-mono text-[11px] text-slate-400">
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
                            Stage Execution Telemetry:
                          </div>
                          <pre className="text-slate-300 whitespace-pre-wrap break-all text-[10px] leading-relaxed">
                            {JSON.stringify(stage.meta, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 4. Executed Tools Telemetry Section */}
          {tools.length > 0 && (
            <div className="pt-3 border-t border-slate-800/80">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <Database className="w-3 h-3 text-sky-400" />
                  <span>Deterministic Tool Invocations ({tools.length})</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  DUCKDB IN-MEMORY COLUMNAR
                </span>
              </div>

              <div className="space-y-1.5">
                {tools.map((t, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded bg-[#0d131f] border border-slate-800 text-xs font-mono space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-sky-400 font-semibold">{t.name}</span>
                        <span
                          className={`text-[9px] px-1 py-0.2 rounded uppercase border ${
                            t.cache === 'hit'
                              ? 'bg-emerald-950 text-emerald-400 border-emerald-500/30'
                              : 'bg-slate-900 text-slate-400 border-slate-800'
                          }`}
                        >
                          CACHE {t.cache}
                        </span>
                      </div>
                      <div className="text-slate-400 text-[11px] tabular-nums">
                        <span>{t.duration_ms.toFixed(1)}ms</span>
                        <span className="text-slate-600 mx-1.5">·</span>
                        <span>{t.rows_out} rows returned</span>
                      </div>
                    </div>

                    {/* Tool Arguments */}
                    {t.args && Object.keys(t.args).length > 0 && (
                      <div className="text-[10px] text-slate-400 bg-slate-950 p-1.5 rounded border border-slate-850 truncate">
                        <span className="text-slate-500">args: </span>
                        <span>{JSON.stringify(t.args)}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
