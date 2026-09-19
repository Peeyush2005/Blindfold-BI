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

      {/* 8-Stage Execution Pipeline Map */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <div className="border-b border-slate-800 pb-4 mb-6">
          <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center space-x-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            <span>The 8-Stage Blindfold BI Execution Pipeline</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Every user prompt traverses this deterministic, audited path before any response is rendered.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

          {/* Stage 1 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 relative">
            <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold mb-1">Stage 01</div>
            <h4 className="text-sm font-semibold text-white">Intent & Question Parsing</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Tokenizes the executive input string and extracts primary operational entities, timeframes, and metric categories.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 relative">
            <div className="text-[10px] font-mono text-amber-400 uppercase font-bold mb-1">Stage 02</div>
            <h4 className="text-sm font-semibold text-white">Metric Contract Resolution</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Cross-references keywords against <code className="text-amber-300 font-mono">metric_contract.yaml</code> to disambiguate GST, realization, and pipeline formulas.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 relative">
            <div className="text-[10px] font-mono text-purple-400 uppercase font-bold mb-1">Stage 03</div>
            <h4 className="text-sm font-semibold text-white">Tool Routing & Execution</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Selects the exact analytical tool (pipeline, revenue, cross-board conversion, or data debt) and sets strict filters.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="bg-slate-950 border border-emerald-800/50 rounded-xl p-4 relative ring-1 ring-emerald-500/20">
            <div className="text-[10px] font-mono text-emerald-400 uppercase font-bold mb-1">Stage 04 • PRIVACY</div>
            <h4 className="text-sm font-semibold text-white">Blindfold Privacy Gateway</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Bi-directional de-identification scrubs all client codes, deal names, and personnel into ephemeral tokens like <span className="text-emerald-300 font-mono">CLIENT_ENT_088</span>.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="bg-slate-950 border border-indigo-800/50 rounded-xl p-4 relative ring-1 ring-indigo-500/20">
            <div className="text-[10px] font-mono text-indigo-400 uppercase font-bold mb-1">Stage 05 • ZERO-MATH</div>
            <h4 className="text-sm font-semibold text-white">NVIDIA NIM (Llama-3.3-70B)</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Llama-3.3-70B receives strictly tokenized text and pre-computed figures. System instructions forbid mental math.
            </p>
          </div>

          {/* Stage 6 */}
          <div className="bg-slate-950 border border-amber-800/50 rounded-xl p-4 relative ring-1 ring-amber-500/20">
            <div className="text-[10px] font-mono text-amber-400 uppercase font-bold mb-1">Stage 06 • DETERMINISTIC</div>
            <h4 className="text-sm font-semibold text-white">DuckDB Vectorized Engine</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Executes pure analytical SQL across in-memory columnar tables for 342 deals and 175 work orders in under 5ms.
            </p>
          </div>

          {/* Stage 7 */}
          <div className="bg-slate-950 border border-rose-800/50 rounded-xl p-4 relative ring-1 ring-rose-500/20">
            <div className="text-[10px] font-mono text-rose-400 uppercase font-bold mb-1">Stage 07 • AUDIT</div>
            <h4 className="text-sm font-semibold text-white">Hallucination Verifier</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Scans generated text and extracts every numeric token, converting Crore/Lakh scales to mathematically match DuckDB ground truth.
            </p>
          </div>

          {/* Stage 8 */}
          <div className="bg-slate-950 border border-teal-800/50 rounded-xl p-4 relative ring-1 ring-teal-500/20">
            <div className="text-[10px] font-mono text-teal-400 uppercase font-bold mb-1">Stage 08 • TRUST</div>
            <h4 className="text-sm font-semibold text-white">De-Anonymizer & Receipts</h4>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Rehydrates session tokens back to readable names in the executive's browser and signs the Cryptographic Trust Receipt.
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
                    <span>Live 8-stage visual simulator + Cryptographic Trust Receipts</span>
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
