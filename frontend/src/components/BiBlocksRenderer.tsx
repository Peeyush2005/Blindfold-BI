import React from 'react';
import { ShieldCheck, Info, AlertTriangle } from 'lucide-react';
import type { GeneratedBlock, TrustReceipt, StarterChip } from '../types';
import { EChartRenderer } from './EChartRenderer';

interface BiBlocksRendererProps {
  blocks: GeneratedBlock[];
  receipt?: TrustReceipt;
  chips?: StarterChip[];
  onChipClick?: (query: string) => void;
}

export const BiBlocksRenderer: React.FC<BiBlocksRendererProps> = ({
  blocks,
  receipt,
  chips,
  onChipClick,
}) => {
  return (
    <div className="space-y-4 my-2 text-slate-200">
      {/* 1. Render all generated BI blocks strictly from tool results */}
      {blocks.map((block, idx) => {
        switch (block.kind) {
          case 'text':
            return (
              <div key={idx} className="text-sm leading-relaxed text-slate-300 whitespace-pre-line">
                {block.content}
              </div>
            );

          case 'kpi':
            return (
              <div
                key={idx}
                className="inline-block m-1.5 p-3.5 rounded-md border border-slate-800 bg-slate-900/80 min-w-[200px]"
              >
                <div className="text-xs font-medium text-slate-400 mb-1">{block.label}</div>
                <div className="text-xl font-semibold text-slate-100 font-mono tabular-nums">
                  {block.display}
                </div>
                {(block.delta !== null && block.delta !== undefined) || block.coverage ? (
                  <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                    {block.delta !== null && block.delta !== undefined && (
                      <span className={block.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {block.delta >= 0 ? `+${block.delta}%` : `${block.delta}%`}
                      </span>
                    )}
                    {block.coverage && <span>{block.coverage}</span>}
                  </div>
                ) : null}
              </div>
            );

          case 'chart':
            return <EChartRenderer key={idx} block={block} />;

          case 'table':
            return (
              <div key={idx} className="my-3 overflow-hidden rounded-md border border-slate-800 bg-slate-900/60">
                {block.title && (
                  <div className="px-3 py-2 text-xs font-medium text-slate-400 border-b border-slate-800 bg-slate-900/90">
                    {block.title}
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900 text-slate-400 font-medium">
                        {block.columns.map((col, cIdx) => (
                          <th key={cIdx} className="px-3 py-2 font-medium">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {block.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-800/30 transition-colors">
                          {row.map((cell, cellIdx) => (
                            <td key={cellIdx} className="px-3 py-2 font-mono tabular-nums text-slate-300">
                              {typeof cell === 'number' ? cell.toLocaleString('en-IN') : String(cell ?? '—')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );

          case 'note':
            return (
              <div
                key={idx}
                className={`my-2 p-3 rounded-md border text-xs flex items-start space-x-2.5 ${
                  block.note_type === 'data_quality'
                    ? 'border-amber-500/30 bg-amber-500/5 text-amber-300'
                    : block.note_type === 'caveat'
                    ? 'border-sky-500/30 bg-sky-500/5 text-sky-300'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400'
                }`}
              >
                {block.note_type === 'data_quality' ? (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                ) : (
                  <Info className="w-4 h-4 shrink-0 text-sky-400 mt-0.5" />
                )}
                <div className="leading-relaxed">{block.text}</div>
              </div>
            );

          default:
            return null;
        }
      })}

      {/* 2. Trust Receipt Badge */}
      {receipt && (
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-500">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-slate-400">
              Verified: {receipt.rows_scanned} rows scanned · {receipt.rows_excluded} excluded ·{' '}
              {receipt.execution_duration_ms.toFixed(1)}ms
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <span>Confidence: {(receipt.confidence_score * 100).toFixed(0)}%</span>
            <span>·</span>
            <span>As of: {receipt.data_as_of}</span>
          </div>
        </div>
      )}

      {/* 3. Follow-up Suggestion Chips (up to 3) */}
      {chips && chips.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800/60">
          <div className="text-[11px] font-medium text-slate-400 mb-2">Related Follow-ups:</div>
          <div className="flex flex-wrap gap-2">
            {chips.slice(0, 3).map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChipClick && onChipClick(chip.query || chip.label)}
                className="px-3 py-1.5 rounded text-xs font-normal bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors cursor-pointer"
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
