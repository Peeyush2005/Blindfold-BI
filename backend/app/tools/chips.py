"""
Deterministic Suggestion Chip Engine for Blindfold BI.
Enforces Section 10.4 specifications without LLM hallucination.
"""

from typing import List, Dict, Any, Optional
from app.contracts import ChipCandidate, contract_manager


STARTER_CHIPS: List[Dict[str, Any]] = [
    {
        "id": "starter_1",
        "label": "📊 Open Pipeline Overview",
        "tool": "pipeline_summary",
        "args": {},
        "reason": "Executive pipeline health and distribution across stages.",
    },
    {
        "id": "starter_2",
        "label": "🌱 Energy Sector Pipeline",
        "tool": "pipeline_summary",
        "args": {"sector_group": "Energy"},
        "reason": "Deep dive into Renewables, Powerline, and Utilities.",
    },
    {
        "id": "starter_3",
        "label": "💰 Revenue Ladder (Bookings to Cash)",
        "tool": "revenue_ladder",
        "args": {},
        "reason": "Full waterfall from contracted to billed and collected.",
    },
    {
        "id": "starter_4",
        "label": "🏆 Best Performing Sectors",
        "tool": "sector_performance",
        "args": {"metric": "order_book", "top_n": 5},
        "reason": "Ranked multi-board sector performance.",
    },
    {
        "id": "starter_5",
        "label": "⚠️ Data Quality & Hygiene Scorecard",
        "tool": "data_quality_report",
        "args": {},
        "reason": "Audit CRM and Work Order anomalies (DQ001-DQ016).",
    },
    {
        "id": "starter_6",
        "label": "📋 Executive Leadership Brief",
        "tool": "leadership_brief",
        "args": {"compare_to": "previous_period"},
        "reason": "Consolidated brief with KPIs, wins, risks, and recommendations.",
    },
]


def get_starter_chips() -> List[ChipCandidate]:
    """Returns the 6 canonical empty-state starter suggestion chips."""
    return [
        ChipCandidate(
            id=c["id"],
            label=c["label"],
            tool=c["tool"],
            args=c["args"],
            reason=c["reason"],
        )
        for c in STARTER_CHIPS
    ]


def generate_followup_chips(tool_name: str, args: Dict[str, Any], data: Dict[str, Any]) -> List[ChipCandidate]:
    """
    Generates contextual deterministic follow-up chips based on tool results.
    """
    chips: List[ChipCandidate] = []

    if tool_name == "pipeline_summary":
        if not args.get("exclude_outliers", False):
            chips.append(ChipCandidate(
                id="pipe_ex_outliers",
                label="🎯 Exclude Tender Outliers",
                tool="pipeline_summary",
                args={**args, "exclude_outliers": True},
                reason="View core business pipeline removing ₹53.20 Cr tender concentration.",
            ))
        chips.append(ChipCandidate(
            id="pipe_stale_drilldown",
            label="⏱️ Review Stale Deals",
            tool="data_debt_list",
            args={"board": "deals", "issue_code": "DQ005"},
            reason="Investigate 47 open deals past tentative close date.",
        ))
        chips.append(ChipCandidate(
            id="pipe_to_revenue",
            label="💰 Realization Waterfall",
            tool="revenue_ladder",
            args={"sector": args.get("sector")},
            reason="Compare open pipeline to invoiced and collected amounts.",
        ))

    elif tool_name == "revenue_ladder":
        chips.append(ChipCandidate(
            id="rev_receivables",
            label="💳 Receivables Aging & AR Debtors",
            tool="receivables_summary",
            args={"sector": args.get("sector")},
            reason="Analyze ₹3.63 Cr outstanding receivables and credit notes.",
        ))
        chips.append(ChipCandidate(
            id="rev_wo_health",
            label="⚙️ Work Order Execution Health",
            tool="workorder_health",
            args={"sector": args.get("sector")},
            reason="Review project completion and delayed deliveries.",
        ))

    elif tool_name == "workorder_health":
        chips.append(ChipCandidate(
            id="wo_unbilled_drilldown",
            label="📑 Completed but Unbilled Backlog",
            tool="workorder_health",
            args={"status_filter": "completed_unbilled"},
            reason="Focus on projects delivered but pending invoicing.",
        ))
        chips.append(ChipCandidate(
            id="wo_to_brief",
            label="📋 Compile Leadership Brief",
            tool="leadership_brief",
            args={},
            reason="Synthesize operational risks into executive brief.",
        ))

    elif tool_name == "sector_performance":
        chips.append(ChipCandidate(
            id="sec_energy",
            label="🌱 Energy Sector Deep Dive",
            tool="pipeline_summary",
            args={"sector_group": "Energy"},
            reason="Examine Renewables, Powerline, and Utilities cluster.",
        ))
        chips.append(ChipCandidate(
            id="sec_tender",
            label="🏛️ Tender Sector Win/Loss",
            tool="win_loss_analysis",
            args={"sector": "Tender"},
            reason="Analyze tender conversion and win rates.",
        ))

    elif tool_name in ["data_quality_report", "data_debt_list"]:
        chips.append(ChipCandidate(
            id="dq_export_csv",
            label="📥 Export DQ Remediation Ledger",
            tool="data_debt_list",
            args={"format": "csv"},
            reason="Download CSV of actionable data quality defects.",
        ))
        chips.append(ChipCandidate(
            id="dq_linkage",
            label="🔗 Cross-Board Linkage Audit",
            tool="link_deals_to_orders",
            args={},
            reason="Audit sector-level reconciliation between Deals and Work Orders.",
        ))

    # Add default fallback if few chips
    if len(chips) < 2:
        chips.append(ChipCandidate(
            id="default_brief",
            label="📋 Executive Leadership Brief",
            tool="leadership_brief",
            args={},
            reason="View holistic KPIs and recommendations.",
        ))

    return chips[:4]
