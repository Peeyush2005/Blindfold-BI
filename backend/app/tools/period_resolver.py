"""
Period Resolver for Blindfold BI.
Resolves natural-language period phrases into Indian Fiscal Year (April 1 - March 31)
date boundaries and SQL filter clauses.
"""

import re
from typing import Optional, Dict, Any, List
from datetime import date
import pandas as pd

from app.contracts import Fact, ToolResult, ChipCandidate, format_count
from app.tools.receipt import make_trust_receipt
from app.data.normalize.common import DEFAULT_AS_OF_DATE


class PeriodResolution:
    def __init__(
        self,
        raw_text: str,
        fiscal_year: Optional[str] = None,
        fiscal_quarter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sql_filter: Optional[str] = None,
        label: str = "All Time",
    ):
        self.raw_text = raw_text
        self.fiscal_year = fiscal_year
        self.fiscal_quarter = fiscal_quarter
        self.start_date = start_date
        self.end_date = end_date
        self.sql_filter = sql_filter or "1=1"
        self.label = label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sql_filter": self.sql_filter,
            "label": self.label,
        }


def resolve_period_helper(period_expr: Optional[str], date_column: str = "close_date") -> PeriodResolution:
    """
    Parses fiscal period expressions like 'Q1 FY25', 'FY24-25', 'current quarter',
    'last fiscal year', 'YTD' into strict Indian Fiscal Year date ranges.
    """
    if not period_expr or not str(period_expr).strip() or str(period_expr).lower() in ["all", "all time", "total"]:
        return PeriodResolution(raw_text=period_expr or "All Time", label="All Time", sql_filter="1=1")

    clean = str(period_expr).strip().lower()

    # FY pattern: FY24-25, FY 2024-2025, FY25, etc.
    fy_match = re.search(r"fy\s*(\d{2,4})(?:[-/](\d{2,4}))?", clean)
    quarter_match = re.search(r"q([1-4])", clean)

    quarter = f"Q{quarter_match.group(1)}" if quarter_match else None

    # Handle relative references
    if "current quarter" in clean or "this quarter" in clean:
        quarter = "Q4"  # As-of March 2026 is Q4 FY25-26
        clean = "fy25-26"
    elif "last quarter" in clean or "previous quarter" in clean:
        quarter = "Q3"
        clean = "fy25-26"
    elif "current fy" in clean or "this fy" in clean or "current year" in clean:
        clean = "fy25-26"
    elif "last fy" in clean or "previous fy" in clean or "last year" in clean:
        clean = "fy24-25"

    fy_match = re.search(r"fy\s*(\d{2,4})(?:[-/](\d{2,4}))?", clean)
    if fy_match:
        start_yr_str = fy_match.group(1)
        if len(start_yr_str) == 2:
            start_yr = 2000 + int(start_yr_str)
        else:
            start_yr = int(start_yr_str)
        end_yr = start_yr + 1
        fy_slug = f"FY{str(start_yr)[-2:]}-{str(end_yr)[-2:]}"
    else:
        # Default fallback to FY25-26 if quarter only
        if quarter:
            start_yr = 2025
            end_yr = 2026
            fy_slug = "FY25-26"
        else:
            return PeriodResolution(raw_text=period_expr, label=period_expr, sql_filter="1=1")

    # Date ranges (Indian Fiscal Year: April 1 to March 31)
    quarter_dates = {
        "Q1": (f"{start_yr}-04-01", f"{start_yr}-06-30"),
        "Q2": (f"{start_yr}-07-01", f"{start_yr}-09-30"),
        "Q3": (f"{start_yr}-10-01", f"{start_yr}-12-31"),
        "Q4": (f"{end_yr}-01-01", f"{end_yr}-03-31"),
    }

    if quarter:
        s_date, e_date = quarter_dates[quarter]
        label = f"{fy_slug} {quarter}"
        sql_filter = f"({date_column} >= '{s_date}' AND {date_column} <= '{e_date}')"
        return PeriodResolution(
            raw_text=period_expr,
            fiscal_year=fy_slug,
            fiscal_quarter=quarter,
            start_date=s_date,
            end_date=e_date,
            sql_filter=sql_filter,
            label=label,
        )
    else:
        s_date = f"{start_yr}-04-01"
        e_date = f"{end_yr}-03-31"
        label = fy_slug
        sql_filter = f"({date_column} >= '{s_date}' AND {date_column} <= '{e_date}')"
        return PeriodResolution(
            raw_text=period_expr,
            fiscal_year=fy_slug,
            fiscal_quarter=None,
            start_date=s_date,
            end_date=e_date,
            sql_filter=sql_filter,
            label=label,
        )


def resolve_period(
    text: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    date_column: str = "close_date",
) -> ToolResult:
    """
    Tool: Resolves natural language date/fiscal expressions into Indian Fiscal Year
    date boundaries and SQL filter clauses.
    """
    expr = text
    if not expr and start and end:
        expr = f"{start} to {end}"

    res = resolve_period_helper(expr, date_column=date_column)

    facts = [
        Fact(
            id="F1",
            metric="period_label",
            label="Resolved Period Label",
            value=res.label,
            unit="text",
            display=res.label,
            dimensions={"raw_text": res.raw_text or "All Time"},
        ),
        Fact(
            id="F2",
            metric="fiscal_year",
            label="Fiscal Year",
            value=res.fiscal_year or "N/A",
            unit="text",
            display=res.fiscal_year or "All Time",
        ),
    ]
    if res.fiscal_quarter:
        facts.append(
            Fact(
                id="F3",
                metric="fiscal_quarter",
                label="Fiscal Quarter",
                value=res.fiscal_quarter,
                unit="text",
                display=res.fiscal_quarter,
            )
        )
    if res.start_date and res.end_date:
        facts.extend([
            Fact(
                id="F4",
                metric="start_date",
                label="Start Date",
                value=res.start_date,
                unit="text",
                display=res.start_date,
            ),
            Fact(
                id="F5",
                metric="end_date",
                label="End Date",
                value=res.end_date,
                unit="text",
                display=res.end_date,
            ),
            Fact(
                id="F6",
                metric="period_start_date",
                label="Start Date",
                value=res.start_date,
                unit="text",
                display=res.start_date,
            ),
            Fact(
                id="F7",
                metric="period_end_date",
                label="End Date",
                value=res.end_date,
                unit="text",
                display=res.end_date,
            ),
        ])

    followups = [
        ChipCandidate(
            id="chip_pipeline",
            label=f"📊 Pipeline in {res.label}",
            tool="pipeline_summary",
            args={"period": res.label},
            reason=f"Analyze open deals in {res.label}",
        ),
        ChipCandidate(
            id="chip_revenue",
            label=f"💰 Revenue in {res.label}",
            tool="revenue_ladder",
            args={"period": res.label},
            reason=f"Examine billing and realization in {res.label}",
        ),
    ]

    template = f"Resolved period '{res.raw_text}' to Indian Fiscal Year calendar: [[F1]] (Start: {res.start_date or 'Beginning'}, End: {res.end_date or 'Present'})."

    receipt = make_trust_receipt(
        tool_name="resolve_period",
        sql_executed=f"-- Resolved period filter: {res.sql_filter}",
        duration_ms=0.5,
        row_count=1,
    )

    return ToolResult(
        tool="resolve_period",
        facts=facts,
        tables=[],
        charts=[],
        followups=followups,
        template=template,
        audit=receipt,
    )
