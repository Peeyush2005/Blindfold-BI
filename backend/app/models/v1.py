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
    call: Literal["plan", "narrate"]
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    queue_ms: float = 0.0
    duration_ms: float = 0.0
    degraded: bool = False


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "connected": True,
                "source": "monday.com",
                "synced_at": "14:32",
                "as_of_date": "15 Jan 2026",
                "deals_count": 332,
                "work_orders_count": 176,
                "display_badge": "monday.com · synced 14:32 · as of 15 Jan 2026"
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
