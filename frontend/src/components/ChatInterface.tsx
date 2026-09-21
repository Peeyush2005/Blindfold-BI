import { useState, useEffect, useRef } from 'react';
import { Send, AlertCircle, Sparkles } from 'lucide-react';
import { apiUrl } from '../apiConfig';
import type {
  AnswerPayload,
  StageState,
  ToolEventData,
  LlmEventData,
  StageName,
} from '../types';
import { RunPanel } from './RunPanel';
import { BiBlocksRenderer } from './BiBlocksRenderer';

const INITIAL_STAGES: StageName[] = [
  'understand',
  'plan',
  'fetch',
  'normalize',
  'compute',
  'narrate',
  'verify',
  'finalize',
];

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  question?: string;
  timestamp: string;
  stages?: StageState[];
  tools?: ToolEventData[];
  llmCalls?: LlmEventData[];
  totalMs?: number;
  degraded?: boolean;
  isCompleted?: boolean;
  isError?: boolean;
  errorMessage?: string;
  answer?: AnswerPayload;
}

interface ChatInterfaceProps {
  triggerQuery?: string | null;
  onQueryTriggered?: () => void;
}

const STARTER_CATEGORIES = [
  {
    title: 'Pipeline',
    chips: [
      {
        label: 'Open Pipeline Overview',
        query: "How's our pipeline looking for the energy sector this quarter?",
        desc: 'Energy cluster open pipeline in Q4 FY25-26',
      },
      {
        label: 'Top Open Pipeline Sector',
        query: 'Which sector has the biggest open pipeline?',
        desc: 'Rank sectors by open pipeline valuation',
      },
    ],
  },
  {
    title: 'Revenue',
    chips: [
      {
        label: 'Revenue Realization Ladder',
        query: 'What did we bill against contracted value?',
        desc: 'Bookings to billing and cash waterfall',
      },
      {
        label: 'Cash Collections & Balance',
        query: 'How much cash have we collected?',
        desc: 'Bank collections and outstanding balance',
      },
    ],
  },
  {
    title: 'Operations',
    chips: [
      {
        label: 'Active Work Orders Health',
        query: 'Which work orders are still ongoing?',
        desc: 'Incomplete project status and delivery dates',
      },
      {
        label: 'Deals to Orders Linkage',
        query: 'Can we join deals and work orders?',
        desc: 'Cross-board keyless audit (DQ015)',
      },
    ],
  },
  {
    title: 'Data Quality',
    chips: [
      {
        label: 'Data Quality Scorecard',
        query: 'How healthy is our data?',
        desc: 'Audit CRM and Work Order anomalies',
      },
      {
        label: 'Stale Pipeline Deals',
        query: 'Any stale open deals?',
        desc: 'Deals inactive for >90 days in open pipeline',
      },
    ],
  },
];

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  triggerQuery,
  onQueryTriggered,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [liveAriaStatus, setLiveAriaStatus] = useState<string>('Ready');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Trigger programmatic query if passed from parent (e.g. Info tab "Ask the agent" links)
  useEffect(() => {
    if (triggerQuery && triggerQuery.trim() && !isLoading) {
      handleSendMessage(triggerQuery.trim());
      if (onQueryTriggered) {
        onQueryTriggered();
      }
    }
  }, [triggerQuery, isLoading]);

  // Verify analytical API connectivity on mount
  useEffect(() => {
    const checkApiConnectivity = async () => {
      try {
        const res = await fetch(apiUrl('/api/v1/tools/starter-chips'));
        if (!res.ok) {
          throw new Error(`API responded with status ${res.status}`);
        }
        setApiError(null);
      } catch (err: any) {
        console.error('Failed to verify API connectivity:', err);
        setApiError('API unreachable: Unable to connect to analytical server.');
      }
    };

    checkApiConnectivity();
  }, []);

  const handleSendMessage = async (queryText: string, chipText?: string) => {
    const question = (queryText || chipText || '').trim();
    if (!question || isLoading) return;

    setApiError(null);
    setIsLoading(true);
    setInputQuery('');
    setLiveAriaStatus(`Analyzing query: ${question}`);

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `asst-${Date.now()}`;

    // Add user message
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      question: question,
      timestamp: new Date().toLocaleTimeString(),
    };

    // Initialize assistant message with 8 queued stages
    const initialStageStates: StageState[] = INITIAL_STAGES.map((name) => ({
      name,
      status: 'queued',
    }));

    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      sender: 'assistant',
      timestamp: new Date().toLocaleTimeString(),
      stages: initialStageStates,
      tools: [],
      llmCalls: [],
      totalMs: 0,
      degraded: false,
      isCompleted: false,
      isError: false,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const sessionId = `sess_${Date.now()}`;

    try {
      const response = await fetch(apiUrl('/api/v1/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: question,
          chip: chipText,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Readable stream not supported by server');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          if (!block.trim()) continue;

          // Lines starting with colon are SSE comments (e.g. : keepalive)
          const lines = block.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith(':')) {
              // Ignore keepalive comment
              continue;
            } else if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6).trim();
            }
          }

          if (!eventType || !dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            handleSseEvent(assistantMsgId, eventType, data);
          } catch (jsonErr) {
            console.warn('Failed to parse SSE JSON:', jsonErr, dataStr);
          }
        }
      }
    } catch (err: any) {
      console.error('Chat execution error:', err);
      setApiError(`API Unreachable: ${err.message || 'Connection lost'}`);
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === assistantMsgId) {
            return {
              ...msg,
              isCompleted: true,
              isError: true,
              errorMessage: err.message || 'API connection failed',
            };
          }
          return msg;
        })
      );
    } finally {
      setIsLoading(false);
      setLiveAriaStatus('Ready');
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleSseEvent = (messageId: string, eventType: string, data: any) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId) return msg;

        switch (eventType) {
          case 'run.started':
            setLiveAriaStatus(`Pipeline run started for ${data.question}`);
            return msg;

          case 'stage': {
            setLiveAriaStatus(`Stage ${data.name}: ${data.status}`);
            const updatedStages = (msg.stages || []).map((st) => {
              if (st.name === data.name) {
                return {
                  ...st,
                  status: data.status,
                  started_at: data.started_at,
                  duration_ms: data.duration_ms,
                  meta: data.meta,
                };
              }
              return st;
            });
            return { ...msg, stages: updatedStages };
          }

          case 'tool': {
            const currentTools = msg.tools || [];
            return {
              ...msg,
              tools: [...currentTools, data as ToolEventData],
            };
          }

          case 'llm': {
            const currentLlm = msg.llmCalls || [];
            return {
              ...msg,
              llmCalls: [...currentLlm, data as LlmEventData],
            };
          }

          case 'answer': {
            return {
              ...msg,
              answer: data as AnswerPayload,
            };
          }

          case 'run.finished': {
            setLiveAriaStatus('Pipeline run finished');
            return {
              ...msg,
              totalMs: data.total_ms,
              degraded: data.degraded || msg.degraded,
              isCompleted: true,
              isError: false,
            };
          }

          case 'run.error': {
            setLiveAriaStatus(`Pipeline error: ${data.message}`);
            return {
              ...msg,
              isCompleted: true,
              isError: true,
              errorMessage: data.message,
            };
          }

          default:
            return msg;
        }
      })
    );
  };

  const handleReplay = (messageId: string) => {
    const targetMsg = messages.find((m) => m.id === messageId);
    if (!targetMsg || !targetMsg.stages) return;

    const originalStages = [...targetMsg.stages];

    // Reset all stages to queued
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? {
              ...m,
              stages: INITIAL_STAGES.map((name) => ({ name, status: 'queued' })),
            }
          : m
      )
    );

    // Progressively replay through each stage
    originalStages.forEach((stage, idx) => {
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== messageId) return m;
            const updated = (m.stages || []).map((s) => (s.name === stage.name ? stage : s));
            return { ...m, stages: updated };
          })
        );
      }, (idx + 1) * 180);
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4.5rem)] max-w-[760px] mx-auto w-full px-4 text-slate-200">
      {/* Hidden aria-live announcer for screen reader accessibility */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {liveAriaStatus}
      </div>

      {/* Global API Error Alert (No canned data fallback) */}
      {apiError && (
        <div
          role="alert"
          className="my-3 p-3 rounded-md border border-rose-500/40 bg-rose-500/10 text-rose-300 text-xs flex items-center space-x-2.5"
        >
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{apiError}</span>
        </div>
      )}

      {/* Messages Scroll Area or Empty State */}
      <div className="flex-1 overflow-y-auto py-4 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-center px-2 py-6">
            <div className="w-10 h-10 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-sky-400 mb-3">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-medium text-slate-100 tracking-tight">
              Skylark Business Intelligence
            </h1>
            <p className="text-xs text-slate-400 mt-1.5 max-w-md">
              Ask any question about pipeline, revenue, work orders, and data hygiene.
            </p>

            {/* Starter Suggestion Chips Grouped under Pipeline, Revenue, Operations, Data quality */}
            <div className="mt-6 w-full space-y-4 text-left">
              {STARTER_CATEGORIES.map((cat) => (
                <div key={cat.title}>
                  <div className="text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1">
                    {cat.title}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {cat.chips.map((chip, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(chip.query)}
                        disabled={isLoading}
                        className="p-2.5 text-left rounded-md border border-slate-800/90 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 text-xs text-slate-300 hover:text-white transition-colors cursor-pointer group"
                      >
                        <div className="font-medium text-slate-200 group-hover:text-sky-300 transition-colors">
                          {chip.label}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                          {chip.desc}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="space-y-2">
              {msg.sender === 'user' ? (
                <div className="flex justify-end">
                  <div className="max-w-xl px-4 py-2.5 rounded-md bg-slate-800 text-slate-100 text-sm border border-slate-700">
                    {msg.question}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col space-y-2">
                  {/* Live / Collapsible 8-stage Run Panel */}
                  {msg.stages && msg.stages.length > 0 && (
                    <RunPanel
                      stages={msg.stages}
                      tools={msg.tools || []}
                      totalMs={msg.totalMs}
                      isCompleted={Boolean(msg.isCompleted)}
                      isError={Boolean(msg.isError)}
                      degraded={Boolean(msg.degraded)}
                      onReplay={() => handleReplay(msg.id)}
                      model={
                        msg.answer?.receipt?.model ||
                        (msg.llmCalls && msg.llmCalls.length > 0
                          ? msg.llmCalls[msg.llmCalls.length - 1].model
                          : undefined)
                      }
                      llmCalled={
                        msg.answer?.receipt?.llm_called ??
                        (msg.llmCalls && msg.llmCalls.length > 0
                          ? msg.llmCalls.some((c) => c.llm_called)
                          : undefined)
                      }
                      narrationSource={
                        msg.answer?.receipt?.narration_source ||
                        (msg.llmCalls && msg.llmCalls.length > 0
                          ? msg.llmCalls[msg.llmCalls.length - 1].narration_source
                          : undefined)
                      }
                      templateReason={
                        msg.answer?.receipt?.template_reason ||
                        (msg.llmCalls && msg.llmCalls.length > 0
                          ? msg.llmCalls[msg.llmCalls.length - 1].template_reason
                          : undefined)
                      }
                    />
                  )}

                  {/* Error display if run failed */}
                  {msg.isError && msg.errorMessage && (
                    <div className="p-3 rounded-md border border-rose-500/30 bg-rose-500/5 text-rose-300 text-xs">
                      {msg.errorMessage}
                    </div>
                  )}

                  {/* Generated BI Blocks strictly produced by analytical tools */}
                  {msg.answer && msg.answer.blocks && (
                    <BiBlocksRenderer
                      blocks={msg.answer.blocks}
                      receipt={msg.answer.receipt}
                      chips={msg.answer.chips}
                      onChipClick={(chipQuery) => handleSendMessage('', chipQuery)}
                    />
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Persistent Bottom Query Input Bar */}
      <div className="py-3 border-t border-slate-800 bg-slate-950">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage(inputQuery);
          }}
          className="flex items-center space-x-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask a question about pipeline, revenue, work orders, or data quality..."
            disabled={isLoading}
            className="flex-1 px-3.5 py-2.5 rounded-md bg-slate-900 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors disabled:opacity-50"
            aria-label="Ask analytical query"
          />
          <button
            type="submit"
            disabled={isLoading || !inputQuery.trim()}
            className="px-4 py-2.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex items-center space-x-1.5"
            aria-label="Send query"
          >
            <span>Ask</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
