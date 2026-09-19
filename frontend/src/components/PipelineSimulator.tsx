import React, { useState, useEffect } from 'react';
import {
  Play, Pause, RotateCcw, CheckCircle2, Clock,
  ShieldCheck, Cpu, Database, Terminal, ArrowRight, Lock,
  Check, FileCheck, Layers, ChevronRight
} from 'lucide-react';
import type { PipelineStepEvent } from '../types';

interface PipelineSimulatorProps {
  steps: PipelineStepEvent[];
  queryText?: string;
  isExecuting?: boolean;
}

export const PipelineSimulator: React.FC<PipelineSimulatorProps> = ({
  steps,
  queryText,
  isExecuting = false,
}) => {
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1000); // ms per step

  // Auto-select latest step when new steps arrive or select first
  useEffect(() => {
    if (steps.length > 0) {
      setActiveStepIndex(steps.length - 1);
    }
  }, [steps.length]);

  // Simulation playback timer
  useEffect(() => {
    let interval: any = null;
    if (isPlaying && steps.length > 0) {
      interval = setInterval(() => {
        setActiveStepIndex((prev) => {
          if (prev >= steps.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, playbackSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, steps.length, playbackSpeed]);

  const currentStep = steps[activeStepIndex] || steps[0];

  const getStepIcon = (stepNum: number) => {
    switch (stepNum) {
      case 1: return <Terminal className="w-4 h-4 text-sky-400" />;
      case 2: return <Layers className="w-4 h-4 text-amber-400" />;
      case 3: return <Cpu className="w-4 h-4 text-purple-400" />;
      case 4: return <Lock className="w-4 h-4 text-emerald-400" />;
      case 5: return <SparklesIcon className="w-4 h-4 text-indigo-400" />;
      case 6: return <Database className="w-4 h-4 text-amber-500" />;
      case 7: return <FileCheck className="w-4 h-4 text-rose-400" />;
      case 8: return <ShieldCheck className="w-4 h-4 text-teal-400" />;
      default: return <ChevronRight className="w-4 h-4 text-slate-400" />;
    }
  };

  const getPrivacyNotice = (stepNum: number) => {
    switch (stepNum) {
      case 4:
        return "🛡️ Blindfold Privacy Gateway: Real client codes, deal titles, and employee names were sanitized into ephemeral session tokens (e.g. CLIENT_ENT_088). No PII leaves the local boundary.";
      case 5:
        return "⚡ NVIDIA NIM (Llama-3.3-70B): Received strictly tokenized text and pre-computed analytical figures. Prompt engineering forbids mental arithmetic.";
      case 6:
        return "🧮 DuckDB Deterministic Engine: Executed pure vectorized SQL directly over 342 deals and 175 work orders. Zero LLM hallucinations in totals or percentages.";
      case 7:
        return "🔍 Hallucination Verifier: Scanned LLM response text, converting metrics to Crore/Lakh scales to mathematically match ground truth. Fabricated numbers are rejected.";
      case 8:
        return "✨ De-anonymizer & Trust Receipt: Safely rehydrated tokens back to human-readable names for executive review alongside an immutable cryptographic audit receipt.";
      default:
        return null;
    }
  };

  if (!steps || steps.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center text-slate-400">
        <Cpu className={`w-12 h-12 mx-auto text-slate-600 mb-3 ${isExecuting ? 'animate-spin text-cyan-400' : 'animate-pulse'}`} />
        <h3 className="text-sm font-semibold text-slate-200">
          {isExecuting ? 'Tracing Live Execution Pipeline...' : 'Simulation Engine Ready'}
        </h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
          {isExecuting
            ? 'Intercepting parameters, tokenizing PII, running DuckDB queries, and querying NVIDIA NIM...'
            : 'Submit an executive query or choose a suggestion chip to trace the 8-stage Blindfold BI privacy and verification pipeline in real-time.'}
        </p>
      </div>
    );
  }

  const totalDuration = steps.reduce((acc, s) => acc + (s.duration_ms || 0), 0);

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 lg:p-6 shadow-2xl backdrop-blur-xl">

      {/* Simulator Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 mb-5 border-b border-slate-800 gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <span className={`flex h-2.5 w-2.5 rounded-full ${isExecuting ? 'bg-amber-400 animate-ping' : 'bg-cyan-400'}`} />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 font-mono m-0">
              Live Pipeline Workflow Simulator
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-cyan-400 font-mono border border-slate-700">
              8 Stages Verified
            </span>
          </div>
          {queryText && (
            <p className="text-xs text-slate-400 mt-1 max-w-xl truncate">
              Tracing Query: <span className="text-slate-200 font-mono">"{queryText}"</span>
            </p>
          )}
        </div>

        {/* Playback Controls & Speed Toggle */}
        <div className="flex items-center space-x-2">
          {/* Speed Selector */}
          <div className="hidden sm:flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[11px] font-mono text-slate-400">
            <button
              onClick={() => setPlaybackSpeed(1500)}
              className={`px-2 py-1 rounded ${playbackSpeed === 1500 ? 'bg-slate-800 text-cyan-300' : 'hover:text-white'}`}
            >
              0.5x
            </button>
            <button
              onClick={() => setPlaybackSpeed(1000)}
              className={`px-2 py-1 rounded ${playbackSpeed === 1000 ? 'bg-slate-800 text-cyan-300' : 'hover:text-white'}`}
            >
              1.0x
            </button>
            <button
              onClick={() => setPlaybackSpeed(500)}
              className={`px-2 py-1 rounded ${playbackSpeed === 500 ? 'bg-slate-800 text-cyan-300' : 'hover:text-white'}`}
            >
              2.0x
            </button>
          </div>

          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              onClick={() => {
                if (activeStepIndex >= steps.length - 1) setActiveStepIndex(0);
                setIsPlaying(!isPlaying);
              }}
              className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center space-x-1 transition"
              title={isPlaying ? "Pause Simulation" : "Auto-Play Simulation"}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{isPlaying ? 'Pause' : 'Simulate'}</span>
            </button>

            <button
              onClick={() => {
                setIsPlaying(false);
                setActiveStepIndex(0);
              }}
              className="p-1.5 text-slate-400 hover:text-white transition"
              title="Reset to Step 1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
            Total: <span className="text-emerald-400 font-bold">{totalDuration.toFixed(1)}ms</span>
          </div>
        </div>
      </div>

      {/* 8-Stage Node Pipeline Visualization */}
      <div className="relative mb-6">
        <div className="overflow-x-auto pb-4 pt-2">
          <div className="flex items-center min-w-[780px] justify-between relative px-2">

            {/* Connecting Track Line */}
            <div className="absolute top-1/2 left-6 right-6 h-[2px] bg-slate-800 -translate-y-1/2 z-0" />

            {steps.map((step, idx) => {
              const isActive = idx === activeStepIndex;
              const isPast = idx < activeStepIndex;
              return (
                <div key={step.step_number} className="relative z-10 flex flex-col items-center">
                  <button
                    onClick={() => {
                      setIsPlaying(false);
                      setActiveStepIndex(idx);
                    }}
                    className={`group relative flex items-center justify-center w-11 h-11 rounded-xl transition-all duration-300 ${
                      isActive
                        ? 'bg-gradient-to-tr from-indigo-600 to-cyan-500 text-white shadow-lg shadow-cyan-500/30 ring-4 ring-cyan-500/20 scale-110'
                        : isPast
                        ? 'bg-slate-800 text-emerald-400 border border-emerald-600/40 hover:scale-105'
                        : 'bg-slate-950 text-slate-500 border border-slate-800 hover:border-slate-700 hover:text-slate-300'
                    }`}
                  >
                    {isPast ? <Check className="w-4 h-4 text-emerald-400" /> : getStepIcon(step.step_number)}

                    {/* Status Pill on top of node */}
                    <span className="absolute -top-2 -right-1 text-[9px] font-mono px-1 py-0.2 rounded-full bg-slate-900 border border-slate-700 text-slate-300">
                      {step.step_number}
                    </span>
                  </button>

                  {/* Step Short Label */}
                  <span className={`text-[10px] font-medium mt-2 text-center max-w-[85px] truncate transition ${
                    isActive ? 'text-cyan-400 font-semibold' : 'text-slate-400'
                  }`}>
                    {step.step_name.split(' ')[0]} {step.step_name.split(' ')[1] || ''}
                  </span>

                  {/* Duration Badge */}
                  <span className="text-[9px] font-mono text-slate-500 mt-0.5">
                    {step.duration_ms}ms
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Step Inspector Panel */}
      {currentStep && (
        <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 lg:p-5 transition-all">

          {/* Top Bar of Inspector */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800/80">
            <div className="flex items-center space-x-2.5">
              <div className="p-1.5 rounded-lg bg-indigo-950/70 border border-indigo-700/50">
                {getStepIcon(currentStep.step_number)}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                  <span>Step {currentStep.step_number}: {currentStep.step_name}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase ${
                    currentStep.status === 'success' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    currentStep.status === 'warning' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {currentStep.status}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">{currentStep.summary}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
              <span className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>{currentStep.duration_ms} ms</span>
              </span>
            </div>
          </div>

          {/* Privacy & Architecture Guarantee Callout */}
          {getPrivacyNotice(currentStep.step_number) && (
            <div className="mb-4 p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start space-x-2">
              <div className="mt-0.5">{getStepIcon(currentStep.step_number)}</div>
              <div className="leading-relaxed">
                {getPrivacyNotice(currentStep.step_number)}
              </div>
            </div>
          )}

          {/* Two-Column Payload Inspector (Input vs Output) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Input Payload */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
                <span className="font-semibold text-slate-300 flex items-center space-x-1">
                  <ArrowRight className="w-3 h-3 text-cyan-400" />
                  <span>Input Payload</span>
                </span>
                <span className="text-[10px] text-slate-500">JSON</span>
              </div>
              <pre className="bg-slate-900 border border-slate-800/80 rounded-lg p-3 text-[11px] font-mono text-cyan-300/90 overflow-x-auto max-h-48 overflow-y-auto leading-tight select-all">
                {JSON.stringify(currentStep.input_payload || {}, null, 2)}
              </pre>
            </div>

            {/* Output Payload */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
                <span className="font-semibold text-slate-300 flex items-center space-x-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Output Payload</span>
                </span>
                <span className="text-[10px] text-slate-500">JSON</span>
              </div>
              <pre className="bg-slate-900 border border-slate-800/80 rounded-lg p-3 text-[11px] font-mono text-emerald-300/90 overflow-x-auto max-h-48 overflow-y-auto leading-tight select-all">
                {JSON.stringify(currentStep.output_payload || {}, null, 2)}
              </pre>
            </div>

          </div>

        </div>
      )}

    </div>
  );
};

function SparklesIcon(props: any) {
  return (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  );
}
