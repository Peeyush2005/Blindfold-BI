"""
Pydantic schemas and typed definitions for Blindfold BI API v1.
Strictly defines API requests, responses, SSE event payloads,
and Generated BI Blocks.
"""

from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Generated BI Blocks (Section 4)
# -----------------------------------------------------------------------------

class TextBlock(BaseModel):
    kind: Literal["text"] = "text"
    content: str = Field(description="Prose narrative with facts verified and substituted")


class KpiBlock(BaseModel):
    kind: Literal["kpi"] = "kpi"
    label: str
    value: float
    display: str
    unit: str
    delta: Optional[float] = None
    coverage: Optional[str] = None


class ChartBlock(BaseModel):
    kind: Literal["chart"] = "chart"
    chart_type: Literal["bar", "line", "funnel", "donut", "waterfall", "heatmap"] = "bar"
    title: str
    data: Any
    format: str = "INR_CR"
    option: Optional[Dict[str, Any]] = None


class TableBlock(BaseModel):
    kind: Literal["table"] = "table"
    title: Optional[str] = None
    columns: List[str]
    rows: List[List[Any]] = Field(description="Maximum 10 rows")


class NoteBlock(BaseModel):
    kind: Literal["note"] = "note"
    note_type: Literal["assumption", "data_quality", "caveat"]
    text: str


GeneratedBlock = Union[TextBlock, KpiBlock, ChartBlock, TableBlock, NoteBlock]


# -----------------------------------------------------------------------------
# Trust Receipt & Chips
# -----------------------------------------------------------------------------

class TrustReceiptV1(BaseModel):
    query_executed: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rows_scanned: int = 0
    rows_excluded: int = 0
    exclusion_reasons: List[str] = Field(default_factory=list)
    execution_duration_ms: float = 0.0
    confidence_score: float = 1.0
    facts_grounded: int = 0
    data_as_of: str = "15 Jan 2026"
    verified: bool = True
    model: Optional[str] = None
    llm_called: bool = False
    narration_source: Literal["llm", "llm_repaired", "template"] = "template"
    template_reason: Optional[Literal["no_api_key", "llm_error", "verifier_rejected", "llm_mode_off"]] = None


class SuggestionChipV1(BaseModel):
    label: str
    query: str
    is_clarification: bool = False


# -----------------------------------------------------------------------------
# Chat Request & Answer Payloads
# -----------------------------------------------------------------------------

class ChatRequestV1(BaseModel):
    session_id: Optional[str] = Field(default="default-session", description="Session identifier")
    question: Optional[str] = Field(default=None, description="User natural language question")
    chip: Optional[str] = Field(default=None, description="Suggestion chip text clicked by user")

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "sess_123",
                "question": "How is the energy pipeline this quarter?"
            }
        }
    }


class AnswerPayload(BaseModel):
    blocks: List[Dict[str, Any]] = Field(default_factory=list)
    receipt: TrustReceiptV1
    chips: List[SuggestionChipV1] = Field(default_factory=list)
    clarification: Optional[bool] = False


# -----------------------------------------------------------------------------
# SSE Event Payloads (Section 3)
# -----------------------------------------------------------------------------

class RunStartedPayload(BaseModel):
    run_id: str
    question: str
    as_of: str = "15 Jan 2026"
    source: str = "monday.com"


class StageEventPayload(BaseModel):
    name: Literal["understand", "plan", "fetch", "normalize", "compute", "narrate", "verify", "finalize"]
    status: Literal["running", "done", "warn", "error", "skipped"]
    started_at: float
    duration_ms: float
    meta: Dict[str, Any] = Field(default_factory=dict)


class ToolEventPayload(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    rows_in: int = 0
    rows_out: int = 0
    excluded: List[Dict[str, Any]] = Field(default_factory=list)
    cache: Literal["hit", "miss"] = "hit"
    duration_ms: float = 0.0


class LlmEventPayload(BaseModel):
    call: Literal["plan", "narrate", "repair"]
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    queue_ms: float = 0.0
    duration_ms: float = 0.0
    degraded: bool = False
    llm_called: bool = False
    narration_source: Literal["llm", "llm_repaired", "template"] = "template"
    template_reason: Optional[Literal["no_api_key", "llm_error", "verifier_rejected", "llm_mode_off"]] = None


class RunFinishedPayload(BaseModel):
    total_ms: float
    degraded: bool = False


class RunErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool = False


# -----------------------------------------------------------------------------
# Meta & Run Inspection Models
# -----------------------------------------------------------------------------

class MetaSourceResponse(BaseModel):
    connected: bool
    source: str
    synced_at: str
    as_of_date: str = "15 Jan 2026"
    deals_count: int = 332
    work_orders_count: int = 176
    display_badge: str
    board_names: List[str] = Field(default_factory=lambda: ["Deal funnel", "Work_Order_Tracker"])
    is_stale: bool = False
    snapshot_age_seconds: Optional[int] = 0
    refresh_policy: str = "Auto-sync every 10 minutes (single-flight background refresh)"

    model_config = {
        "json_schema_extra": {
            "example": {
                "connected": True,
                "source": "monday.com",
                "synced_at": "14:32",
                "as_of_date": "15 Jan 2026",
                "deals_count": 332,
                "work_orders_count": 176,
                "display_badge": "monday.com · synced 14:32 · as of 15 Jan 2026",
                "board_names": ["Deal funnel", "Work_Order_Tracker"],
                "is_stale": False,
                "snapshot_age_seconds": 120,
                "refresh_policy": "Auto-sync every 10 minutes (single-flight background refresh)",
            }
        }
    }


class DQCodeSummary(BaseModel):
    code: str
    name: str
    count: int
    severity: str
    why_it_matters: str
    example_query: str


class MetaQualityResponse(BaseModel):
    rows_loaded: Dict[str, int]
    rows_used: Dict[str, int]
    duplicates_removed: int = 0
    header_rows_removed: int = 0
    share_of_deals_with_no_value: str
    empty_columns: List[str]
    dq_codes: List[DQCodeSummary]
    total_anomalies: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "rows_loaded": {"deals": 332, "work_orders": 176},
                "rows_used": {"deals": 332, "work_orders": 176},
                "duplicates_removed": 0,
                "header_rows_removed": 0,
                "share_of_deals_with_no_value": "8.7% (29 deals)",
                "empty_columns": ["deal_funnel.unused_notes", "work_orders.legacy_id"],
                "dq_codes": [
                    {
                        "code": "DQ003",
                        "name": "Missing Deal Value",
                        "count": 29,
                        "severity": "high",
                        "why_it_matters": "Deals with missing values are excluded from pipeline aggregates to prevent undercounting.",
                        "example_query": "Which deals have missing values?",
                    }
                ],
                "total_anomalies": 84,
            }
        }
    }


class MetaContractResponse(BaseModel):
    as_of_date: str = "15 Jan 2026"
    energy_sector_group: Dict[str, Any]
    fiscal_year_policy: Dict[str, Any]
    probability_weights: Dict[str, float]
    cross_board_join_policy: str
    metric_definitions: List[Dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "example": {
                "as_of_date": "15 Jan 2026",
                "energy_sector_group": {
                    "name": "Energy Cluster",
                    "sectors": ["Renewables", "Powerline"],
                    "description": "Aggregated energy verticals representing green energy and powerline transmission assets in the dataset.",
                },
                "fiscal_year_policy": {
                    "start_month": 4,
                    "current_fy": "FY25-26",
                    "current_quarter": "Q4 FY25-26",
                    "quarter_range": "1 Jan 2026 - 31 Mar 2026",
                },
                "probability_weights": {
                    "Lead": 0.10,
                    "Qualified": 0.25,
                    "Proposal": 0.50,
                    "Negotiation": 0.75,
                    "Won": 1.00,
                    "Lost": 0.00,
                },
                "cross_board_join_policy": "No reliable deal-to-work-order key exists (DQ015). Cross-board joins without surrogate foreign keys are strictly refused.",
                "metric_definitions": [
                    {
                        "name": "open_pipeline",
                        "display_name": "Open Pipeline Value",
                        "basis": "Excl. GST, Known Values Only",
                        "formula": "SUM(deal_value) WHERE stage NOT IN ('Won', 'Lost')",
                    }
                ],
            }
        }
    }



class RunRecord(BaseModel):
    run_id: str
    question: str
    as_of: str = "15 Jan 2026"
    source: str = "monday.com"
    status: Literal["running", "completed", "error"] = "completed"
    total_ms: float = 0.0
    degraded: bool = False
    stages: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    answer: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    created_at: float
