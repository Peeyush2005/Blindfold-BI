// Typed analytical BI schemas for Blindfold BI

export interface MetaSource {
  connected: boolean;
  source: string;
  synced_at: string;
  as_of_date: string;
  deals_count: number;
  work_orders_count: number;
  display_badge: string;
}

export interface StarterChip {
  id?: string;
  label: string;
  tool?: string;
  args?: Record<string, any>;
  reason?: string;
  query?: string;
  is_clarification?: boolean;
}

// -----------------------------------------------------------------------------
// Generated BI Blocks (Section 4)
// -----------------------------------------------------------------------------

export interface TextBlock {
  kind: 'text';
  content: string;
}

export interface KpiBlock {
  kind: 'kpi';
  label: string;
  value: number;
  display: string;
  unit: string;
  delta?: number | null;
  coverage?: string | null;
}

export interface ChartBlock {
  kind: 'chart';
  chart_type: 'bar' | 'line' | 'funnel' | 'donut' | 'waterfall' | 'heatmap';
  title: string;
  data: any;
  format?: string;
  option?: any;
}

export interface TableBlock {
  kind: 'table';
  title?: string | null;
  columns: string[];
  rows: any[][];
}

export interface NoteBlock {
  kind: 'note';
  note_type: 'assumption' | 'data_quality' | 'caveat';
  text: string;
}

export type GeneratedBlock = TextBlock | KpiBlock | ChartBlock | TableBlock | NoteBlock;

// -----------------------------------------------------------------------------
// Trust Receipt
// -----------------------------------------------------------------------------

export interface TrustReceipt {
  query_executed: string;
  parameters: Record<string, any>;
  rows_scanned: number;
  rows_excluded: number;
  exclusion_reasons: string[];
  execution_duration_ms: number;
  confidence_score: number;
  facts_grounded: number;
  data_as_of: string;
  verified: boolean;
}

export interface AnswerPayload {
  blocks: GeneratedBlock[];
  receipt: TrustReceipt;
  chips: StarterChip[];
  clarification?: boolean;
}

// -----------------------------------------------------------------------------
// Real-time Pipeline Stage States (Section 2 & 3)
// -----------------------------------------------------------------------------

export type StageName =
  | 'understand'
  | 'plan'
  | 'fetch'
  | 'normalize'
  | 'compute'
  | 'narrate'
  | 'verify'
  | 'finalize';

export type StageStatus = 'queued' | 'running' | 'done' | 'warn' | 'error' | 'skipped';

export interface StageState {
  name: StageName;
  status: StageStatus;
  started_at?: number;
  duration_ms?: number;
  meta?: Record<string, any>;
}

export interface ToolEventData {
  name: string;
  args: Record<string, any>;
  rows_in: number;
  rows_out: number;
  excluded: Array<{ code: string; count: number }>;
  cache: 'hit' | 'miss';
  duration_ms: number;
}

export interface LlmEventData {
  call: 'plan' | 'narrate';
  model: string;
  tokens_in: number;
  tokens_out: number;
  queue_ms: number;
  duration_ms: number;
  degraded: boolean;
}

export interface RunFinishedData {
  total_ms: number;
  degraded: boolean;
}

export interface RunErrorData {
  code: string;
  message: string;
  retryable: boolean;
}

export interface RunRecord {
  run_id: string;
  question: string;
  as_of: string;
  source: string;
  status: 'running' | 'completed' | 'error';
  total_ms: number;
  degraded: boolean;
  stages: StageState[];
  events: any[];
  answer?: AnswerPayload | null;
  error?: RunErrorData | null;
  created_at: number;
}
