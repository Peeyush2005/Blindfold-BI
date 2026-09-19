from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default-session"
    parameters: Optional[Dict[str, Any]] = None

class PipelineStepEvent(BaseModel):
    step_number: int
    step_name: str
    status: str = "success"  # success, in_progress, skipped, warning
    duration_ms: float = 0.0
    input_payload: Any = None
    output_payload: Any = None
    summary: str = ""

class TrustReceipt(BaseModel):
    query_executed: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rows_scanned: int = 0
    rows_excluded: int = 0
    exclusion_reasons: List[str] = Field(default_factory=list)
    execution_duration_ms: float = 0.0
    confidence_score: float = 1.0
    facts_grounded: int = 0
    data_as_of: str = ""
    verified: bool = True

class SuggestionChip(BaseModel):
    label: str
    query: str
    is_clarification: bool = False

class ChatResponse(BaseModel):
    answer: str
    trust_receipt: TrustReceipt
    suggestion_chips: List[SuggestionChip] = Field(default_factory=list)
    pipeline_trace: List[PipelineStepEvent] = Field(default_factory=list)
    chart_data: Optional[Dict[str, Any]] = None
    facts: Optional[List[Dict[str, Any]]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    dq_warnings: Optional[List[Dict[str, Any]]] = None
    tool_result: Optional[Dict[str, Any]] = None

class DashboardOverview(BaseModel):
    pipeline_value: float
    weighted_pipeline_value: float
    won_deal_value: float
    wo_contracted_value: float
    wo_billed_value: float
    wo_collected_value: float
    wo_receivable_value: float
    wo_unbilled_backlog: float
    realization_rate_pct: float
    collection_efficiency_pct: float
    deal_to_wo_conversion_pct: float
    data_debt_count: int
    funnel_stages: List[Dict[str, Any]]
    sector_breakdown: List[Dict[str, Any]]
    financial_waterfall: List[Dict[str, Any]]
    execution_breakdown: List[Dict[str, Any]]

class DataDebtItem(BaseModel):
    id: str
    type: str  # "deal" | "work_order"
    entity_name: str
    owner: str
    sector: str
    issue_category: str
    severity: str  # "High" | "Medium" | "Low"
    description: str
    recommended_action: str
