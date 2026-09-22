"""
Metadata, Data Quality ledger, and Contract definition endpoints for Blindfold BI API v1.
Powers Info Tab transparency and audit centers.
"""

from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter
from app.config import settings
from app.models.v1 import (
    MetaSourceResponse,
    MetaQualityResponse,
    MetaContractResponse,
    DQCodeSummary,
)
from app.data.adapter import adapter
from app.data.dq_ledger import dq_ledger
from app.data.normalize.deals import PROB_WEIGHTS, DEFAULT_PROB_WEIGHT

router = APIRouter(prefix="/meta", tags=["Metadata & Transparency v1"])


DQ_EXPLANATIONS: Dict[str, Dict[str, str]] = {
    "DQ001": {
        "why": "Stray header rows inside data tables were removed to prevent string conversion failures in numeric columns.",
        "query": "How healthy is our data?",
    },
    "DQ002": {
        "why": "Duplicate records were deduplicated to prevent double-counting pipeline valuation and billed totals.",
        "query": "Were any duplicate items found in our pipeline?",
    },
    "DQ003": {
        "why": "Deals with missing or null values cannot be summed; they are tracked separately as a coverage caveat.",
        "query": "Which deals have missing values?",
    },
    "DQ004": {
        "why": "Unassigned deals lack account executives or client entities, affecting sales territory attribution.",
        "query": "Which deals lack owner assignments?",
    },
    "DQ005": {
        "why": "Deals in open stages with no activity for >90 days indicate stalled or abandoned opportunities.",
        "query": "Any stale open deals?",
    },
    "DQ006": {
        "why": "Deals marked Won while still in early stages represent CRM workflow sequence violations.",
        "query": "Are there any won deals with stage mismatch?",
    },
    "DQ007": {
        "why": "Outsized government tender bids skew average deal metrics and require isolated statistical handling.",
        "query": "How much of the pipeline is Tender?",
    },
    "DQ008": {
        "why": "Custom columns with 100% null entries add visual clutter without analytical value and are ignored.",
        "query": "Which columns in our boards are completely empty?",
    },
    "DQ009": {
        "why": "Over-collected payments or credit memos where cash exceeds invoiced revenue are flagged for review.",
        "query": "Are there any negative receivables?",
    },
    "DQ014": {
        "why": "Work orders completed without an issued invoice represent unbilled work in progress.",
        "query": "What is our unbilled work order balance?",
    },
    "DQ015": {
        "why": "No verified foreign key exists between Deals and Work Orders; cross-board joins are strictly refused.",
        "query": "Can we join deals and work orders?",
    },
}


@router.get(
    "/source",
    response_model=MetaSourceResponse,
    summary="Get Connected Data Source Status",
    description="Reports the real data source (monday.com, stale_snapshot, or unavailable), the actual sync time, snapshot age, and row counts from the last fetch. Exposes zero secrets.",
)
async def get_source_metadata():
    status = await adapter.ensure_fresh()
    as_of = settings.AS_OF_DATE
    stats = status.get("stats") or {}
    boards = stats.get("boards") or {}
    board_names = [b.get("board_name") for b in boards.values() if b.get("board_name")]
    synced_at = adapter.last_synced.strftime("%H:%M") if adapter.last_synced else "never"

    if not status.get("has_data"):
        source_name, badge = "unavailable", "monday.com not connected"
    elif status.get("is_stale"):
        source_name, badge = "stale_snapshot", f"Stale snapshot · last synced {synced_at} · as of {as_of}"
    elif status.get("source") == "monday.com":
        source_name, badge = "monday.com", f"monday.com · synced {synced_at} · as of {as_of}"
    else:
        source_name, badge = status.get("source") or "snapshot", f"Local fixture (not live) · loaded {synced_at} · as of {as_of}"

    return MetaSourceResponse(
        connected=bool(status.get("connected")),
        source=source_name,
        synced_at=synced_at,
        as_of_date=as_of,
        deals_count=int(status.get("deals_count") or 0),
        work_orders_count=int(status.get("work_orders_count") or 0),
        display_badge=badge,
        board_names=board_names,
        is_stale=bool(status.get("is_stale")),
        snapshot_age_seconds=status.get("snapshot_age_seconds"),
        refresh_policy=f"Re-reads monday.com when the snapshot is older than {settings.CACHE_TTL_SECONDS // 60} minutes",
    )


@router.get(
    "/quality",
    response_model=MetaQualityResponse,
    summary="Get Data Quality Ledger Summary",
    description="Audit totals computed from the last real fetch: rows loaded vs used, duplicates and header rows removed, missing-value share, empty columns, and the DQ anomaly breakdown.",
)
async def get_quality_metadata():
    status = await adapter.ensure_fresh()
    anomalies = dq_ledger.get_all()
    rows = (status.get("stats") or {}).get("rows", {})
    dq_summaries: List[DQCodeSummary] = []
    total_count = 0

    for a in anomalies:
        expl = DQ_EXPLANATIONS.get(a.code, {})
        dq_summaries.append(
            DQCodeSummary(
                code=a.code,
                name=a.rule_name,
                count=a.affected_count,
                severity=a.severity.lower(),
                why_it_matters=expl.get("why", a.description),
                example_query=expl.get("query", f"Show details for {a.rule_name}"),
            )
        )
        total_count += a.affected_count

    def affected(code: str) -> int:
        item = next((a for a in anomalies if a.code == code), None)
        return int(item.affected_count) if item else 0

    deals_clean = int(rows.get("deals_clean") or 0)
    missing_values = affected("DQ003")
    share = (missing_values / deals_clean * 100) if deals_clean else 0.0
    dq008 = next((a for a in anomalies if a.code == "DQ008"), None)

    return MetaQualityResponse(
        rows_loaded={"deals": int(rows.get("deals_raw") or 0), "work_orders": int(rows.get("work_orders_raw") or 0)},
        rows_used={"deals": deals_clean, "work_orders": int(rows.get("work_orders_clean") or 0)},
        duplicates_removed=affected("DQ002"),
        header_rows_removed=affected("DQ001"),
        share_of_deals_with_no_value=f"{share:.1f}% ({missing_values} deals)",
        empty_columns=list(dq008.sample_identifiers) if dq008 else [],
        dq_codes=dq_summaries,
        total_anomalies=total_count,
    )


def _energy_description() -> str:
    df = adapter.deals_df
    if df is None:
        return "Energy = Renewables + Powerline. Data not loaded yet."
    counts = df["sector"].value_counts()
    ren, pwr = int(counts.get("Renewables", 0)), int(counts.get("Powerline", 0))
    return (
        f"Energy is Renewables ({ren} deals) plus Powerline ({pwr} deals) in the connected Deals board. "
        "There is no sector literally named Energy, Power, or Utilities in the data."
    )


@router.get(
    "/contract",
    response_model=MetaContractResponse,
    summary="Get Contract Governance & Definitions",
    description="Returns metric definitions, GST calculation bases, fiscal calendar policies, canonical Energy sector groupings, and probability weights.",
)
async def get_contract_metadata():
    metric_defs = [
        {
            "name": "open_pipeline",
            "display_name": "Open Pipeline Value",
            "basis": "Excl. GST, Known Values Only",
            "formula": "SUM(deal_value) WHERE status = 'Open'",
            "description": "Total unclosed pipeline opportunity value across active sales stages.",
        },
        {
            "name": "weighted_pipeline",
            "display_name": "Weighted Pipeline Value",
            "basis": "Excl. GST, Multiplied by Stage Probability",
            "formula": "SUM(deal_value * stage_probability) WHERE status = 'Open'",
            "description": "Risk-adjusted pipeline valuation based on historical stage conversion rates.",
        },
        {
            "name": "won_deal_value",
            "display_name": "Closed Won Value",
            "basis": "Excl. GST",
            "formula": "SUM(deal_value) WHERE stage = 'Won' OR status = 'Won'",
            "description": "Total contracted deal value closed successfully.",
        },
        {
            "name": "contracted_work_orders",
            "display_name": "Contracted Work Order Amount",
            "basis": "Excl. GST",
            "formula": "SUM(amount_excl_gst)",
            "description": "Total approved work order bookings recognized in operations tracker.",
        },
        {
            "name": "billed_work_orders",
            "display_name": "Billed Invoiced Value",
            "basis": "Excl. GST",
            "formula": "SUM(billed_excl_gst)",
            "description": "Total invoiced milestone revenue recognized against contracted work orders.",
        },
        {
            "name": "collected_cash",
            "display_name": "Collected Cash Amount",
            "basis": "Incl. GST (Bank Receipt Basis)",
            "formula": "SUM(collected_incl_gst)",
            "description": "Actual cash collected into corporate bank accounts including GST pass-through.",
        },
        {
            "name": "outstanding_receivables",
            "display_name": "Outstanding Receivables",
            "basis": "Excl. GST (Billed minus Collected Net)",
            "formula": "SUM(receivable_amount)",
            "description": "Pending accounts receivable due from clients on invoiced milestones.",
        },
    ]

    return MetaContractResponse(
        as_of_date=settings.AS_OF_DATE,
        energy_sector_group={
            "name": "Energy Cluster",
            "sectors": ["Renewables", "Powerline"],
            "description": _energy_description(),
        },
        fiscal_year_policy={
            "start_month": 4,
            "current_fy": "FY25-26",
            "current_quarter": "Q4 FY25-26",
            "quarter_range": "1 Jan 2026 – 31 Mar 2026",
            "as_of_date": settings.AS_OF_DATE,
        },
        probability_weights={**PROB_WEIGHTS, "Not recorded": DEFAULT_PROB_WEIGHT},
        cross_board_join_policy="No verified foreign key exists between Deals and Work Orders (DQ015). Cross-board relational joins are strictly refused to guarantee zero Cartesian hallucination.",
        metric_definitions=metric_defs,
    )
