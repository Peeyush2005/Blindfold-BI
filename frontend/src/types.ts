// Typed analytical BI schemas for Blindfold BI

export interface MetaSource {
  connected: boolean;
  source: string;
  synced_at: string;
  as_of_date: string;
  deals_count: number;
  work_orders_count: number;
  display_badge: string;
  board_names?: string[];
  is_stale?: boolean;
  snapshot_age_seconds?: number;
  refresh_policy?: string;
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
// Info Tab Metadata Schemas (Section 7)
// -----------------------------------------------------------------------------

export interface DQCodeSummary {
  code: string;
  name: string;
  count: number;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  why_it_matters: string;
  example_query: string;
}

export interface MetaQuality {
  rows_loaded: Record<string, number>;
  rows_used: Record<string, number>;
  duplicates_removed: number;
  header_rows_removed: number;
  share_of_deals_with_no_value: string;
  empty_columns: string[];
  dq_codes: DQCodeSummary[];
  total_anomalies: number;
}

export interface MetricDefinition {
  name: string;
  display_name: string;
  basis: string;
  formula: string;
  description: string;
}

export interface EnergySectorGroup {
  name: string;
  sectors: string[];
  description: string;
}

export interface FiscalYearPolicy {
  start_month: number;
  current_fy: string;
  current_quarter: string;
  quarter_range: string;
  as_of_date: string;
}

export interface MetaContract {
  as_of_date: string;
  energy_sector_group: EnergySectorGroup;
  fiscal_year_policy: FiscalYearPolicy;
  probability_weights: Record<string, number>;
  cross_board_join_policy: string;
  metric_definitions: MetricDefinition[];
}

export interface ToolCatalogItem {
  name: string;
  domain: string;
  description: string;
  parameters: Record<string, any>;
  examples?: string[];
}

export interface ReadyzStatus {
  status: string;
  llm: string;
  data_source: string;
  llm_configured: boolean;
  monday_configured: boolean;
  key_store: string;
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
// Trust Receipt & Telemetry (Step 0)
// -----------------------------------------------------------------------------

export type NarrationSource = 'llm' | 'llm_repaired' | 'template';
export type TemplateReason = 'no_api_key' | 'llm_error' | 'verifier_rejected' | 'llm_mode_off';

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
  model?: string;
  llm_called?: boolean;
  narration_source?: NarrationSource;
  template_reason?: TemplateReason | null;
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
  call: 'plan' | 'narrate' | 'repair';
  model: string;
  tokens_in?: number;
  tokens_out?: number;
  queue_ms?: number;
  duration_ms?: number;
  degraded?: boolean;
  llm_called?: boolean;
  narration_source?: NarrationSource;
  template_reason?: TemplateReason | null;
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
