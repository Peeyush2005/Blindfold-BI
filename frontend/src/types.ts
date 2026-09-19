export interface PipelineStepEvent {
  step_number: number;
  step_name: string;
  status: 'success' | 'warning' | 'error' | 'pending' | 'active';
  duration_ms: number;
  input_payload: Record<string, any>;
  output_payload: Record<string, any>;
  summary: string;
}

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

export interface SuggestionChip {
  label: string;
  query: string;
  is_clarification?: boolean;
}

export interface ChartData {
  type: 'waterfall' | 'bar' | 'pie' | 'line';
  title: string;
  categories?: string[];
  values?: number[];
  data?: Array<{ name: string; value: number }>;
}

export interface ChatResponse {
  answer: string;
  trust_receipt: TrustReceipt;
  suggestion_chips: SuggestionChip[];
  pipeline_trace: PipelineStepEvent[];
  chart_data?: ChartData;
}

export interface DashboardOverview {
  pipeline_value: number;
  weighted_pipeline_value: number;
  won_deal_value: number;
  wo_contracted_value: number;
  wo_billed_value: number;
  wo_collected_value: number;
  wo_receivable_value: number;
  wo_unbilled_backlog: number;
  realization_rate_pct: number;
  collection_efficiency_pct: number;
  deal_to_wo_conversion_pct: number;
  data_debt_count: number;
  funnel_stages: Array<{ stage: string; count: number; value: number }>;
  sector_breakdown: Array<{ sector: string; order_count: number; contracted_excl_gst: number; billed_excl_gst: number }>;
  financial_waterfall: Array<{ name: string; value: number; type: string }>;
  execution_breakdown: Array<{ execution_status: string; count: number; contracted_value: number; billed_value: number }>;
}

export interface DataDebtItem {
  id: string;
  type: string;
  entity_name: string;
  owner: string;
  sector: string;
  issue_category: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  recommended_action: string;
}
