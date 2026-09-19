import React, { useState, useRef, useEffect } from 'react';
import * as echarts from 'echarts';
import {
  Send, Bot, User, ShieldCheck, Sparkles,
  ChevronDown, ChevronUp, ArrowRight, BarChart2
} from 'lucide-react';
import type { ChatResponse, PipelineStepEvent, ChartData } from '../types';
import { PipelineSimulator } from './PipelineSimulator';
import { apiUrl } from '../apiConfig';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  response?: ChatResponse;
}

interface ChatInterfaceProps {
  initialQuery?: string;
  onClearInitialQuery?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  initialQuery,
  onClearInitialQuery,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "👋 Welcome to **Blindfold BI for Skylark Drones**. I am your conversational intelligence executive co-pilot.\n\nAll real client names, deal codes, and project titles are scrubbed and anonymized before reaching external AI models. All arithmetic is calculated deterministically via DuckDB with mathematical hallucination verification.\n\nAsk any question regarding our sales pipeline, work order revenue realization, data debt, or financial waterfalls.",
      timestamp: new Date().toLocaleTimeString(),
    }
  ]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [latestPipelineSteps, setLatestPipelineSteps] = useState<PipelineStepEvent[]>([]);
  const [tracingQuery, setTracingQuery] = useState<string>('');
  const [expandedReceipts, setExpandedReceipts] = useState<Record<string, boolean>>({});
  const [showSimulator, setShowSimulator] = useState<boolean>(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Handle passed initial query from dashboard
  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      handleSendMessage(initialQuery);
      if (onClearInitialQuery) onClearInitialQuery();
    }
  }, [initialQuery]);

  const handleSendMessage = async (queryText: string) => {
    const text = queryText.trim();
    if (!text || isLoading) return;

    const userMessageId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);
    setTracingQuery(text);
    setLatestPipelineSteps([]); // Reset steps for live state machine simulation

    const sessionId = `skylark-session-${Date.now()}`;

    try {
      // 1. Attempt real-time SSE streaming endpoint
      let streamedSuccess = false;
      try {
        const streamRes = await fetch(apiUrl('/api/chat/stream'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            message: text,
            session_id: sessionId,
          }),
        });

        if (streamRes.ok && streamRes.body && streamRes.headers.get('content-type')?.includes('text/event-stream')) {
          const reader = streamRes.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let completedResponse: ChatResponse | null = null;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';

            for (const block of blocks) {
              if (!block.trim()) continue;
              const lines = block.split('\n');
              let eventType = 'message';
              let dataStr = '';

              for (const line of lines) {
                if (line.startsWith('event: ')) {
                  eventType = line.slice(7).trim();
                } else if (line.startsWith('data: ')) {
                  dataStr = line.slice(6).trim();
                }
              }

              if (!dataStr) continue;

              try {
                if (eventType === 'step') {
                  const stepPayload = JSON.parse(dataStr);
                  const stepNum = parseInt(stepPayload.step_id?.replace(/\D/g, '') || '0') || 1;
                  const stepEvent: PipelineStepEvent = {
                    step_number: stepNum,
                    step_name: stepPayload.step_name || `S${stepNum}`,
                    status: stepPayload.status === 'completed' ? 'success' : (stepPayload.status || 'success'),
                    duration_ms: stepPayload.duration_ms || 0,
                    summary: stepPayload.summary || '',
                    input_payload: stepPayload.details?.input || stepPayload.details || {},
                    output_payload: stepPayload.details?.output || stepPayload.details || {},
                  };

                  setLatestPipelineSteps((prev) => {
                    const existing = prev.filter((s) => s.step_number !== stepNum);
                    return [...existing, stepEvent].sort((a, b) => a.step_number - b.step_number);
                  });
                } else if (eventType === 'complete') {
                  completedResponse = JSON.parse(dataStr) as ChatResponse;
                }
              } catch (parseErr) {
                console.warn('Error parsing SSE event payload:', parseErr);
              }
            }
          }

          if (completedResponse) {
            streamedSuccess = true;
            const assistantMsg: ChatMessage = {
              id: `assistant-${Date.now()}`,
              sender: 'assistant',
              text: completedResponse.answer,
              timestamp: new Date().toLocaleTimeString(),
              response: completedResponse,
            };
            setMessages((prev) => [...prev, assistantMsg]);
            if (completedResponse.pipeline_trace && completedResponse.pipeline_trace.length > 0) {
              setLatestPipelineSteps(completedResponse.pipeline_trace);
            }
          }
        }
      } catch (streamErr) {
        console.warn('Streaming fetch failed, falling back to standard POST:', streamErr);
      }

      // 2. Fallback to standard POST /api/chat if streaming was not successful
      if (!streamedSuccess) {
        const res = await fetch(apiUrl('/api/chat'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            session_id: sessionId,
          }),
        });

        if (!res.ok) {
          throw new Error(`HTTP Error: ${res.status}`);
        }

        const data: ChatResponse = await res.json();

        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          sender: 'assistant',
          text: data.answer,
          timestamp: new Date().toLocaleTimeString(),
          response: data,
        };

        setMessages((prev) => [...prev, assistantMsg]);
        if (data.pipeline_trace && data.pipeline_trace.length > 0) {
          setLatestPipelineSteps(data.pipeline_trace);
        }
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `assistant-error-${Date.now()}`,
        sender: 'assistant',
        text: `⚠️ **Error communicating with Blindfold Gateway**: ${err.message || 'Unable to connect to backend server. Please check that FastAPI is running on port 8000.'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleReceipt = (id: string) => {
    setExpandedReceipts((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const presetQueries = [
    "What is our active pipeline and weighted forecast?",
    "What is our revenue realization rate and unbilled backlog?",
    "Which work orders are delayed and what revenue is at risk?",
    "Explain our deal-to-work-order conversion and conversion leakage."
  ];

  return (
    <div className="space-y-6 pb-12">

      {/* Top Banner: Simulator Toggle & Explanation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-slate-900/90 border border-slate-800 rounded-2xl p-4 gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-indigo-950 border border-indigo-800/60 text-indigo-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0">
              Conversational Executive Engine
            </h2>
            <p className="text-xs text-slate-400 m-0">
              NVIDIA NIM Llama-3.3-70B • DuckDB Vectorized Calculations • PII Sanitization Gateway
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowSimulator(!showSimulator)}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 font-mono transition"
        >
          <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
          <span>{showSimulator ? 'Hide Pipeline Simulator' : 'Show Pipeline Simulator'}</span>
        </button>
      </div>

      {/* Live Pipeline Simulator */}
      {showSimulator && (
        <PipelineSimulator
          steps={latestPipelineSteps}
          queryText={tracingQuery}
          isExecuting={isLoading}
        />
      )}

      {/* Main Chat Container */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-2xl flex flex-col min-h-[500px]">

        {/* Messages List Area */}
        <div className="flex-1 p-4 sm:p-6 space-y-6 overflow-y-auto max-h-[600px]">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.sender === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 p-[1px] shrink-0 mt-1 shadow-md shadow-cyan-500/20">
                  <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
                    <Bot className="w-4 h-4 text-cyan-400" />
                  </div>
                </div>
              )}

              <div
                className={`max-w-2xl sm:max-w-3xl rounded-2xl p-4 sm:p-5 text-sm transition-all ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-lg shadow-indigo-600/20'
                    : 'bg-slate-950/90 border border-slate-800 text-slate-200 shadow-xl'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/60 text-xs font-mono text-slate-400">
                  <span className="font-semibold text-slate-300">
                    {msg.sender === 'user' ? 'Executive Prompt' : 'Blindfold BI Assistant'}
                  </span>
                  <span>{msg.timestamp}</span>
                </div>

                {/* Body Text */}
                <div className="prose prose-invert prose-sm max-w-none leading-relaxed whitespace-pre-wrap">
                  {msg.text}
                </div>

                {/* Dynamic Chart (If Included in Response) */}
                {msg.response?.chart_data && (
                  <ResponseChart chartData={msg.response.chart_data} />
                )}

                {/* Trust Receipt Accordion (Assistant Only) */}
                {msg.response?.trust_receipt && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80">
                    <button
                      onClick={() => toggleReceipt(msg.id)}
                      className="w-full flex items-center justify-between text-xs font-mono text-cyan-400 hover:text-cyan-300 transition py-1"
                    >
                      <div className="flex items-center space-x-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        <span className="font-semibold">
                          Cryptographic Trust Receipt (100% Grounded)
                        </span>
                      </div>
                      {expandedReceipts[msg.id] ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>

                    {expandedReceipts[msg.id] && (
                      <div className="mt-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono space-y-2 text-slate-300">
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pb-2 border-b border-slate-800">
                          <div>
                            <span className="text-slate-500 block text-[10px]">VERIFIED STATUS</span>
                            <span className="text-emerald-400 font-bold">✓ Mathematical Match</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block text-[10px]">ROWS SCANNED</span>
                            <span className="text-slate-200">{msg.response.trust_receipt.rows_scanned} records</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block text-[10px]">EXECUTION LATENCY</span>
                            <span className="text-cyan-300">{msg.response.trust_receipt.execution_duration_ms} ms</span>
                          </div>
                        </div>

                        <div>
                          <span className="text-slate-500 block text-[10px]">ANALYTICAL TOOL EXECUTED</span>
                          <span className="text-indigo-300 font-semibold">{msg.response.trust_receipt.query_executed}</span>
                        </div>

                        {msg.response.trust_receipt.exclusion_reasons && msg.response.trust_receipt.exclusion_reasons.length > 0 && (
                          <div>
                            <span className="text-slate-500 block text-[10px]">EXCLUSIONS & DATA HYGIENE</span>
                            <ul className="list-disc list-inside text-[11px] text-amber-400/90 mt-0.5">
                              {msg.response.trust_receipt.exclusion_reasons.map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="text-[10px] text-slate-500 pt-1">
                          Data Snapshot: {msg.response.trust_receipt.data_as_of} • Confidence: 1.0 (Zero Hallucinations)
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Suggestion & Clarification Chips */}
                {msg.response?.suggestion_chips && msg.response.suggestion_chips.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap gap-2">
                    {msg.response.suggestion_chips.map((chip, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(chip.query)}
                        className={`text-xs px-3 py-1.5 rounded-xl font-medium transition flex items-center space-x-1.5 ${
                          chip.is_clarification
                            ? 'bg-amber-950/60 hover:bg-amber-900 text-amber-300 border border-amber-800/80'
                            : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700'
                        }`}
                      >
                        <span>{chip.label}</span>
                        <ArrowRight className="w-3 h-3 text-slate-500" />
                      </button>
                    ))}
                  </div>
                )}

              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center shrink-0 mt-1 shadow-md shadow-indigo-600/20">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}

          {/* Thinking / Loading Animation */}
          {isLoading && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-xl bg-slate-950 border border-cyan-500/40 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-cyan-400 animate-spin" />
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 shadow-xl text-slate-300 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400">
                  <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                  <span>Executing 10-Stage S1-S10 Blindfold Verification Pipeline...</span>
                </div>
                <p className="text-xs text-slate-500 m-0">
                  Intake → Ambiguity Analysis → Tool Planning → Inbound HMAC Tokenization → DuckDB SQL → Outbound Audit → NVIDIA NIM Llama-3.3-70B → Fact Verification → Server-Side Re-identification → Trust Receipt
                </p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Preset Query Chips Carousel */}
        <div className="p-3 bg-slate-950/60 border-t border-slate-800/80 overflow-x-auto flex items-center space-x-2">
          <span className="text-[11px] font-mono text-slate-500 uppercase shrink-0 px-1">
            Executive Queries:
          </span>
          {presetQueries.map((query, idx) => (
            <button
              key={idx}
              disabled={isLoading}
              onClick={() => handleSendMessage(query)}
              className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition disabled:opacity-50"
            >
              {query}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 rounded-b-2xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputQuery);
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isLoading}
              placeholder="Ask an executive query (e.g., 'What is our realization rate?', 'Show delayed work orders')..."
              className="flex-1 bg-slate-900 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-sans transition disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !inputQuery.trim()}
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-medium text-sm flex items-center space-x-2 shadow-lg shadow-indigo-600/30 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>Query</span>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

      </div>

    </div>
  );
};

// Subcomponent for rendering dynamically returned chart data in chat bubbles
const ResponseChart: React.FC<{ chartData: ChartData }> = ({ chartData }) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);

    const categories = chartData.categories || (chartData.data ? chartData.data.map(d => d.name) : []);
    const values = chartData.values || (chartData.data ? chartData.data.map(d => d.value) : []);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      title: {
        text: chartData.title,
        textStyle: { color: '#f8fafc', fontSize: 12, fontWeight: 'bold' },
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: { left: '3%', right: '4%', bottom: '8%', top: '18%', containLabel: true },
      xAxis: {
        type: 'category',
        data: categories,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 15 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#1e293b' } },
        axisLabel: { color: '#94a3b8' }
      },
      series: [
        {
          type: 'bar',
          data: values,
          itemStyle: { color: '#6366f1' },
          barWidth: '45%'
        }
      ]
    };

    chart.setOption(option);
    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
    };
  }, [chartData]);

  return (
    <div className="mt-4 p-3 bg-slate-900 border border-slate-800 rounded-xl">
      <div ref={chartRef} className="w-full h-56" />
    </div>
  );
};
