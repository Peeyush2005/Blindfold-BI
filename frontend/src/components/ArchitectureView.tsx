import React from 'react';
import {
  ShieldCheck, Cpu, FileCheck, Lock,
  Check, X, Layers
} from 'lucide-react';

export const ArchitectureView: React.FC = () => {
  return (
    <div className="space-y-8 pb-16">

      {/* Hero Overview */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 text-xs font-mono mb-4">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Blindfold BI Security & Verification Architecture</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight leading-tight">
            How Skylark Drones Achieves <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400">Zero PII Leakage</span> and <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">Zero Math Hallucinations</span>
          </h2>
          <p className="text-sm text-slate-300 mt-3 leading-relaxed">
            Traditional conversational AI systems expose proprietary customer identities to external cloud models and rely on language models to calculate percentages and currency sums — inevitably producing hallucinations. Blindfold BI decouples reasoning, mathematical computation, and privacy into isolated, verifiable layers.
          </p>
        </div>
      </div>

      {/* 10-Stage Execution Pipeline Map */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <div className="border-b border-slate-800 pb-4 mb-6">
          <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center space-x-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            <span>The 10-Stage Blindfold BI State Machine Pipeline</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Every user prompt traverses this deterministic, audited 10-stage state machine before any response is rendered.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5">

          {/* Stage 1 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-3.5 relative">
            <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold mb-1">S1 • Intake</div>
            <h4 className="text-xs font-semibold text-white">Intake & Normalization</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Strips whitespace, sanitizes prompt text, and extracts temporal qualifiers and sector entities.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-3.5 relative">
            <div className="text-[10px] font-mono text-amber-400 uppercase font-bold mb-1">S2 • Contract</div>
            <h4 className="text-xs font-semibold text-white">Understand & Ambiguity</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Evaluates query against <code className="text-amber-300 font-mono text-[10px]">metric_contract.yaml</code>; produces interactive clarification chips.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-3.5 relative">
            <div className="text-[10px] font-mono text-purple-400 uppercase font-bold mb-1">S3 • Routing</div>
            <h4 className="text-xs font-semibold text-white">Tool Planning</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Selects the single authoritative tool from the 14-tool deterministic DuckDB registry.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="bg-slate-950 border border-emerald-800/50 rounded-xl p-3.5 relative ring-1 ring-emerald-500/20">
            <div className="text-[10px] font-mono text-emerald-400 uppercase font-bold mb-1">S4 • Privacy</div>
            <h4 className="text-xs font-semibold text-white">Blindfold Inbound</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              HMAC-SHA256 tokenization replaces real client names, deal codes, and sales reps with surrogate tokens.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="bg-slate-950 border border-cyan-800/50 rounded-xl p-3.5 relative ring-1 ring-cyan-500/20">
            <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold mb-1">S5 • Compute</div>
            <h4 className="text-xs font-semibold text-white">DuckDB SQL Engine</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Executes sub-5ms vectorized columnar SQL directly on 332 deals and 176 work orders. Zero LLM math.
            </p>
          </div>

          {/* Stage 6 */}
          <div className="bg-slate-950 border border-teal-800/50 rounded-xl p-3.5 relative ring-1 ring-teal-500/20">
            <div className="text-[10px] font-mono text-teal-400 uppercase font-bold mb-1">S6 • Audit</div>
            <h4 className="text-xs font-semibold text-white">Blindfold Outbound</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Audits DuckDB tool output to guarantee zero raw entities cross the boundary before LLM dispatch.
            </p>
          </div>

          {/* Stage 7 */}
          <div className="bg-slate-950 border border-indigo-800/50 rounded-xl p-3.5 relative ring-1 ring-indigo-500/20">
            <div className="text-[10px] font-mono text-indigo-400 uppercase font-bold mb-1">S7 • Synthesis</div>
            <h4 className="text-xs font-semibold text-white">NVIDIA NIM (70B)</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Llama-3.3-70B writes executive commentary citing figures strictly via <code className="text-indigo-300 font-mono text-[10px]">[[F#]]</code> tokens.
            </p>
          </div>

          {/* Stage 8 */}
          <div className="bg-slate-950 border border-rose-800/50 rounded-xl p-3.5 relative ring-1 ring-rose-500/20">
            <div className="text-[10px] font-mono text-rose-400 uppercase font-bold mb-1">S8 • Verifier</div>
            <h4 className="text-xs font-semibold text-white">Fact Verifier</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Audits generated figures across Crore/Lakh units against DuckDB ground truth. Ungrounded claims rejected.
            </p>
          </div>

          {/* Stage 9 */}
          <div className="bg-slate-950 border border-blue-800/50 rounded-xl p-3.5 relative ring-1 ring-blue-500/20">
            <div className="text-[10px] font-mono text-blue-400 uppercase font-bold mb-1">S9 • Rehydrate</div>
            <h4 className="text-xs font-semibold text-white">Controlled Re-ID</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Rehydrates surrogate tokens back to authentic names strictly server-side for display.
            </p>
          </div>

          {/* Stage 10 */}
          <div className="bg-slate-950 border border-emerald-800/50 rounded-xl p-3.5 relative ring-1 ring-emerald-500/20">
            <div className="text-[10px] font-mono text-emerald-400 uppercase font-bold mb-1">S10 • Receipts</div>
            <h4 className="text-xs font-semibold text-white">Trust Receipt</h4>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Signs and returns the response envelope with verified facts, exclusions, and zero-hallucination score.
            </p>
          </div>

        </div>
      </div>

      {/* Architectural Principles Detail */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* Principle 1 */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-950 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
            <Lock className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Zero PII Leakage Guarantee</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Enterprise clients have strict confidentiality agreements. Blindfold Gateway intercepts every outbound prompt payload, substituting sensitive client identifiers, project codenames, and employee initials with deterministic session surrogate tokens. External LLM providers never receive proprietary trade data.
          </p>
        </div>

        {/* Principle 2 */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-950 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Zero LLM Arithmetic</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Large Language Models are probabilistic token generators, fundamentally unsuited for multi-digit financial calculations, ratios, and percentages. In Blindfold BI, 100% of arithmetic is calculated deterministically by DuckDB. The LLM is restricted exclusively to executive synthesis, contextual nuance, and narrative commentary.
          </p>
        </div>

        {/* Principle 3 */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
            <FileCheck className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white">Mathematical Trust Receipts</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Every answer is accompanied by a cryptographic audit receipt detailing exact SQL execution time, record scan count, exclusions, and grounded fact counts. If the LLM generates a number not strictly grounded in DuckDB truth, the Hallucination Verifier triggers an automatic fallback.
          </p>
        </div>

      </div>

      {/* Comparison Table: Traditional Chatbot vs Blindfold BI */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-base font-bold text-white mb-4">
          Architectural Comparison: Traditional BI Chatbot vs. Blindfold BI
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase">
                <th className="py-3 px-4">Feature / Capability</th>
                <th className="py-3 px-4 text-rose-400">Traditional LLM Chatbot (Text-to-SQL / Prompt Dump)</th>
                <th className="py-3 px-4 text-emerald-400">Blindfold BI (Skylark Drones Implementation)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Customer Identity Privacy</td>
                <td className="py-3 px-4 text-slate-400">
                  <div className="flex items-center space-x-1.5 text-rose-400">
                    <X className="w-4 h-4 shrink-0" />
                    <span>Transmits raw company names and deal sizes to public LLM API</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-300">
                  <div className="flex items-center space-x-1.5 text-emerald-400">
                    <Check className="w-4 h-4 shrink-0" />
                    <span>Blindfold Gateway scrubs all PII into session tokens locally</span>
                  </div>
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Financial Calculations</td>
                <td className="py-3 px-4 text-slate-400">
                  <div className="flex items-center space-x-1.5 text-rose-400">
                    <X className="w-4 h-4 shrink-0" />
                    <span>LLM calculates sums and percentages; prone to mental math drift</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-300">
                  <div className="flex items-center space-x-1.5 text-emerald-400">
                    <Check className="w-4 h-4 shrink-0" />
                    <span>100% computed via DuckDB vectorized columnar SQL</span>
                  </div>
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Ambiguity Disambiguation</td>
                <td className="py-3 px-4 text-slate-400">
                  <div className="flex items-center space-x-1.5 text-rose-400">
                    <X className="w-4 h-4 shrink-0" />
                    <span>Guesses whether user means GST inclusive or exclusive</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-300">
                  <div className="flex items-center space-x-1.5 text-emerald-400">
                    <Check className="w-4 h-4 shrink-0" />
                    <span>Explicit Metric Contract with interactive clarification chips</span>
                  </div>
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Hallucination Defense</td>
                <td className="py-3 px-4 text-slate-400">
                  <div className="flex items-center space-x-1.5 text-rose-400">
                    <X className="w-4 h-4 shrink-0" />
                    <span>No post-generation verification; fabricated numbers reach executives</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-300">
                  <div className="flex items-center space-x-1.5 text-emerald-400">
                    <Check className="w-4 h-4 shrink-0" />
                    <span>Hallucination Verifier audits every number against ground truth</span>
                  </div>
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Audit & Transparency</td>
                <td className="py-3 px-4 text-slate-400">
                  <div className="flex items-center space-x-1.5 text-rose-400">
                    <X className="w-4 h-4 shrink-0" />
                    <span>Black box output with zero provenance metadata</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-300">
                  <div className="flex items-center space-x-1.5 text-emerald-400">
                    <Check className="w-4 h-4 shrink-0" />
                    <span>Live 10-stage state machine simulator + Cryptographic Trust Receipts</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
