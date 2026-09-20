import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  MinusCircle,
  ChevronDown,
  ChevronUp,
  RotateCcw,
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
}

const STAGE_LABELS: Record<string, string> = {
  understand: 'Understand (period & scope resolution)',
  plan: 'Plan (analytical tool selection)',
  fetch: 'Fetch (monday.com snapshot cache)',
  normalize: 'Normalize (schema hygiene & DQ ledger)',
  compute: 'Compute (deterministic DuckDB SQL)',
  narrate: 'Narrate (LLM numbers-by-reference)',
  verify: 'Verify (strict numeric reconciliation)',
  finalize: 'Finalize (token rehydration & BI blocks)',
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
}) => {
  // Auto-collapse when run finishes; expand while in progress
  const [expanded, setExpanded] = useState<boolean>(!isCompleted);

  useEffect(() => {
    if (!isCompleted) {
      setExpanded(true);
    } else {
      setExpanded(false);
    }
  }, [isCompleted]);

  const totalRows = tools.reduce((acc, t) => acc + (t.rows_out || t.rows_in || 0), 0);
  const durationSec = totalMs ? (totalMs / 1000).toFixed(1) : '0.0';

  const summaryText = `${stages.length} stages · ${durationSec}s · ${tools.length} tool${tools.length === 1 ? '' : 's'} · ${totalRows} rows`;

  const renderStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <div className="w-3.5 h-3.5 rounded-full border-2 border-sky-400 border-t-transparent animate-spin" />;
      case 'done':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case 'warn':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-rose-500" />;
      case 'skipped':
        return <MinusCircle className="w-4 h-4 text-slate-500" />;
      case 'queued':
      default:
        return <div className="w-3.5 h-3.5 rounded-full border border-slate-600 bg-slate-800" />;
    }
  };

  return (
    <div
      className="my-3 rounded-md border border-slate-800 bg-slate-950 text-slate-200 text-xs overflow-hidden transition-all duration-200"
      aria-live="polite"
      aria-label="Analytical Pipeline Run"
    >
      {/* Header bar / Collapsed single summary line */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-900/90 border-b border-slate-800/80">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {!isCompleted && !isError ? (
              <div className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
            ) : isError ? (
              <div className="w-2 h-2 rounded-full bg-rose-500" />
            ) : (
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
            )}
            <span className="font-mono tabular-nums text-slate-300 font-medium">{summaryText}</span>
          </div>

          {degraded && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Degraded Mode
            </span>
          )}

          {isError && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Execution Error
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {/* Replay button: only available on finished runs, explicitly labelled Replay */}
          {isCompleted && onReplay && (
            <button
              type="button"
              onClick={onReplay}
              disabled={isReplaying}
              className="flex items-center space-x-1 px-2 py-1 rounded text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-800 transition-colors text-[11px]"
              aria-label="Replay run"
            >
              <RotateCcw className={`w-3 h-3 ${isReplaying ? 'animate-spin' : ''}`} />
              <span>Replay</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
            aria-label={expanded ? 'Collapse run details' : 'Expand run details'}
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expanded Live Stage Progression */}
      {expanded && (
        <div className="divide-y divide-slate-900 p-2">
          {stages.map((stage) => {
            const label = STAGE_LABELS[stage.name] || stage.name;
            const duration = stage.duration_ms !== undefined ? `${stage.duration_ms.toFixed(1)}ms` : '—';

            return (
              <div
                key={stage.name}
                className="flex items-center justify-between px-2 py-1.5 hover:bg-slate-900/50 rounded transition-colors"
              >
                <div className="flex items-center space-x-2.5">
                  {renderStatusIcon(stage.status)}
                  <span className="font-medium text-slate-300">{label}</span>
                  {stage.meta && Object.keys(stage.meta).length > 0 && (
                    <span className="text-[11px] font-mono text-slate-500 truncate max-w-xs">
                      {JSON.stringify(stage.meta).replace(/[{"}]/g, ' ')}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-3 text-slate-400 font-mono text-[11px] tabular-nums">
                  <span>{duration}</span>
                  <span className="capitalize text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    {stage.status}
                  </span>
                </div>
              </div>
            );
          })}

          {/* Tools summary if any tools were executed */}
          {tools.length > 0 && (
            <div className="pt-2 mt-2 px-2 border-t border-slate-800/60">
              <div className="text-[11px] font-medium text-slate-400 mb-1.5">Executed Deterministic Tools:</div>
              <div className="space-y-1">
                {tools.map((t, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2 py-1 rounded"
                  >
                    <span className="text-sky-400">{t.name}</span>
                    <span className="tabular-nums text-slate-400">
                      {t.rows_out} rows · {t.duration_ms.toFixed(1)}ms · cache: {t.cache}
                    </span>
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
