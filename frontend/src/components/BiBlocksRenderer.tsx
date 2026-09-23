import React from 'react';
import { ShieldCheck, Info, AlertTriangle, ArrowRight } from 'lucide-react';
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
              <div
                key={idx}
                className="text-[13px] leading-relaxed text-slate-300 font-sans whitespace-pre-line"
              >
                {block.content}
              </div>
            );

          case 'kpi':
            return (
              <div
                key={idx}
                className="inline-block m-1.5 p-3.5 rounded border border-slate-800 bg-[#0d131f] min-w-[210px] shadow-xs"
              >
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                  <span>{block.label}</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                </div>
                <div className="text-2xl font-semibold text-slate-100 font-display tracking-tight tabular-nums">
                  {block.display}
                </div>
                {(block.delta !== null && block.delta !== undefined) || block.coverage ? (
                  <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                    {block.delta !== null && block.delta !== undefined && (
                      <span className={block.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {block.delta >= 0 ? `+${block.delta}%` : `${block.delta}%`}
                      </span>
                    )}
                    {block.coverage && <span className="text-slate-400">{block.coverage}</span>}
                  </div>
                ) : null}
              </div>
            );

          case 'chart':
            return <EChartRenderer key={idx} block={block} />;

          case 'table':
            return (
              <div
                key={idx}
                className="my-3 overflow-hidden rounded border border-slate-800 bg-[#0a0f1b]"
              >
                {block.title && (
                  <div className="px-3.5 py-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 border-b border-slate-800 bg-[#0d131f]">
                    {block.title}
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-[#0d131f]/60 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                        {block.columns.map((col, cIdx) => (
                          <th key={cIdx} className="px-3.5 py-2.5 font-medium">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {block.rows.map((row, rIdx) => (
                        <tr
                          key={rIdx}
                          className="hover:bg-slate-800/25 transition-colors"
                        >
                          {row.map((cell, cellIdx) => (
                            <td
                              key={cellIdx}
                              className="px-3.5 py-2.5 font-mono tabular-nums text-slate-300"
                            >
                              {typeof cell === 'number'
                                ? cell.toLocaleString('en-IN')
                                : String(cell ?? '—')}
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
                className={`my-2 p-3 rounded border text-xs flex items-start space-x-2.5 ${
                  block.note_type === 'data_quality'
                    ? 'border-amber-500/30 bg-amber-500/5 text-amber-300'
                    : block.note_type === 'caveat'
                    ? 'border-sky-500/30 bg-sky-500/5 text-sky-300'
                    : 'border-slate-800 bg-[#0d131f] text-slate-400'
                }`}
              >
                {block.note_type === 'data_quality' ? (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                ) : (
                  <Info className="w-4 h-4 shrink-0 text-sky-400 mt-0.5" />
                )}
                <div className="leading-relaxed font-sans">{block.text}</div>
              </div>
            );

          default:
            return null;
        }
      })}

      {/* 2. Trust Receipt Badge */}
      {receipt && (
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            <span>
              Verified: {receipt.rows_scanned} rows scanned · {receipt.rows_excluded} excluded ·{' '}
              {receipt.execution_duration_ms.toFixed(1)}ms
            </span>
          </div>
          <div className="flex items-center space-x-3 text-slate-500">
            <span>Confidence: {(receipt.confidence_score * 100).toFixed(0)}%</span>
            <span>·</span>
            <span>As of: {receipt.data_as_of}</span>
          </div>
        </div>
      )}

      {/* 3. Follow-up Suggestion Chips (up to 3) */}
      {chips && chips.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800/60">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">
            Follow-up Inquiries:
          </div>
          <div className="flex flex-wrap gap-2">
            {chips.slice(0, 3).map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChipClick && onChipClick(chip.query || chip.label)}
                className="px-3 py-1.5 rounded text-xs font-mono bg-[#0d131f] hover:bg-sky-500/10 text-slate-300 hover:text-sky-300 border border-slate-800 hover:border-sky-500/40 transition-all cursor-pointer flex items-center space-x-1.5"
              >
                <span>{chip.label}</span>
                <ArrowRight className="w-3 h-3 text-slate-500" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
