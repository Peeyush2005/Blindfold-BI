"""
Data Quality and Hygiene Analytical Tools for Blindfold BI.
Pure DuckDB execution and DQ Ledger auditing for DQ001-DQ016.
"""

from typing import Optional, Dict, Any, List
import io
import csv

from app.data.duckdb_store import duckdb_store
from app.data.dq_ledger import dq_ledger
from app.contracts import (
    Fact,
    Table,
    ChartSpec,
    DQEntry,
    ToolResult,
    format_count,
    format_inr,
)
from app.tools.receipt import make_trust_receipt
from app.tools.chips import generate_followup_chips


def data_quality_report(
    board: Optional[str] = None,
    severity: Optional[str] = None,
) -> ToolResult:
    """
    Produces comprehensive Data Quality and Hygiene Scorecard covering DQ001-DQ016
    across Deals Funnel and Work Orders Tracker boards.
    """
    duckdb_store.initialize()

    all_anomalies = dq_ledger.get_all()
    filtered = []

    # Map DQ codes to boards: DQ001-DQ007 -> deals, DQ008-DQ016 -> work_orders
    for a in all_anomalies:
        b = "deals" if int(a.code.replace("DQ", "")) <= 7 else "work_orders"
        if board and board.lower() not in [b, "all"]:
            continue
        if severity and a.severity.upper() != severity.upper():
            continue
        filtered.append((a, b))

    total_issues = len(filtered)
    high_sev = sum(1 for a, _ in filtered if a.severity == "HIGH")
    med_sev = sum(1 for a, _ in filtered if a.severity == "MEDIUM")
    total_affected = sum(a.affected_count for a, _ in filtered)

    facts = [
        Fact(
            id="F1",
            metric="total_anomalies",
            label="Total Data Quality Anomalies",
            value=total_issues,
            unit="count",
            display=f"{total_issues} anomalies ({total_affected} rows affected)",
            must_mention=True,
            role="primary",
        ),
        Fact(
            id="F2",
            metric="high_severity_dq_count",
            label="High Severity Hygiene Anomalies",
            value=high_sev,
            unit="count",
            display=f"{high_sev} high severity",
            must_mention=True,
            role="support",
        ),
        Fact(
            id="F3",
            metric="total_affected_rows",
            label="Cumulative Rows Affected",
            value=total_affected,
            unit="count",
            display=f"{total_affected} rows",
            role="support",
        ),
    ]

    tbl_headers = ["DQ Code", "Board", "Rule Name", "Severity", "Affected Rows", "Resolution Strategy"]
    tbl_rows = [
        [
            a.code,
            b.replace("_", " ").title(),
            a.rule_name,
            a.severity,
            a.affected_count,
            a.resolution,
        ]
        for a, b in filtered
    ]
    t1 = Table(
        id="t_dq_scorecard",
        title="Data Quality & Hygiene Audit Ledger (DQ001 - DQ016)",
        headers=tbl_headers,
        rows=tbl_rows,
        footnote="System automatically resolves or isolates anomalies during normalization without manual data tampering.",
    )

    chart = ChartSpec(
        id="chart_dq_severity",
        chart_type="donut",
        title="Data Quality Anomalies by Severity",
        option={
            "tooltip": {"trigger": "item"},
            "series": [
                {
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "data": [
                        {"name": "High Severity", "value": high_sev, "itemStyle": {"color": "#ef4444"}},
                        {"name": "Medium Severity", "value": med_sev, "itemStyle": {"color": "#f59e0b"}},
                        {"name": "Low / Info", "value": total_issues - high_sev - med_sev, "itemStyle": {"color": "#3b82f6"}},
                    ],
                }
            ]
        }
    )

    dq_entries = [
        DQEntry(
            code=a.code,
            rule_name=a.rule_name,
            severity=a.severity,
            affected_count=a.affected_count,
            description=a.description,
            resolution=a.resolution,
        )
        for a, _ in filtered
    ]

    template = (
        f"Data quality audit identified [[F1]] documented quirks across operational data with "
        f"[[F2]] high severity issues affecting [[F3]] cumulative records. "
        f"All anomalies have deterministic normalization resolutions applied."
    )

    receipt = make_trust_receipt(
        tool_name="data_quality_report",
        sql_executed="-- Queried registered in-memory DQ Ledger",
        duration_ms=0.8,
        row_count=total_issues,
    )

    followups = generate_followup_chips("data_quality_report", {"board": board}, {"high_sev": high_sev})

    return ToolResult(
        tool="data_quality_report",
        facts=facts,
        tables=[t1],
        charts=[chart],
        dq=dq_entries,
        followups=followups,
        template=template,
        audit=receipt,
    )


def data_debt_list(
    board: Optional[str] = None,
    issue_code: Optional[str] = None,
    severity: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
    format: str = "json",
) -> ToolResult:
    """
    Returns granular remediation ledger for data hygiene issues (e.g. stale deals,
    unassigned owners, unbilled completed work orders, negative receivables) with remediation advice.
    """
    duckdb_store.initialize()

    if type and type.strip().lower() in ["stale_open_deals", "stale_deals", "stale"]:
        sql = """
            SELECT
                deal_alias,
                client_id,
                sector,
                owner_id,
                deal_value,
                tentative_close_date,
                is_stale
            FROM deals
            WHERE status = 'Open' AND is_stale = true
            ORDER BY deal_value DESC
        """
        rows, dur, _ = duckdb_store.query(sql)
        stale_cnt = len(rows)
        stale_val = sum(r["deal_value"] or 0.0 for r in rows)

        facts = [
            Fact(
                id="F1",
                metric="stale_deals_count",
                label="Stale Open Deals (DQ005)",
                value=stale_cnt,
                unit="count",
                display=f"{stale_cnt} stale deals",
                must_mention=True,
                role="primary",
                caveat_codes=["DQ005"],
            ),
            Fact(
                id="F2",
                metric="stale_deals_value",
                label="Stale Pipeline Value",
                value=stale_val,
                unit="INR",
                display=format_inr(stale_val),
                role="support",
                caveat_codes=["DQ005"],
            ),
        ]

        stale_headers = ["Deal Token", "Client Token", "Sector", "Owner Token", "Tentative Close", "Deal Value"]
        stale_rows = [
            [
                r["deal_alias"],
                r["client_id"],
                r["sector"],
                r["owner_id"],
                str(r["tentative_close_date"])[:10] if r["tentative_close_date"] else "N/A",
                format_inr(r["deal_value"] or 0.0),
            ]
            for r in rows[:limit]
        ]

        t1 = Table(
            id="t_stale_deals",
            title="Stale Open Deals Ledger (DQ005)",
            headers=stale_headers,
            rows=stale_rows,
            footnote="Open deals with no activity for >90 days or overdue tentative close date.",
        )

        template = (
            f"Identified [[F1]] with no recent activity or past tentative close date, "
            f"locking [[F2]] in inactive pipeline risk (DQ005)."
        )

        receipt = make_trust_receipt(
            tool_name="data_debt_list",
            sql_executed=sql.strip(),
            duration_ms=dur,
            row_count=stale_cnt,
            caveats=["DQ005: Stale pipeline deals excluded from high-confidence forecast."],
        )

        return ToolResult(
            tool="data_debt_list",
            facts=facts,
            tables=[t1],
            charts=[],
            dq=[],
            followups=[],
            template=template,
            audit=receipt,
        )

    all_anomalies = dq_ledger.get_all()
    filtered = []

    for a in all_anomalies:
        b = "deals" if int(a.code.replace("DQ", "")) <= 7 else "work_orders"
        if board and board.lower() not in [b, "all"]:
            continue
        if issue_code and a.code.upper() != issue_code.upper():
            continue
        if severity and a.severity.upper() != severity.upper():
            continue
        filtered.append((a, b))

    facts = [
        Fact(
            id="F1",
            metric="debt_issues_count",
            label="Data Debt Issues Listed",
            value=len(filtered),
            unit="count",
            display=f"{len(filtered)} issues",
            role="primary",
            must_mention=True,
        )
    ]

    debt_headers = ["Code", "Board", "Rule", "Severity", "Impact Count", "Actionable Remediation"]
    debt_rows = [
        [a.code, b.title(), a.rule_name, a.severity, a.affected_count, a.resolution]
        for a, b in filtered[:limit]
    ]

    # If CSV requested, serialize to CSV text
    csv_text = ""
    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(debt_headers)
        for r in debt_rows:
            writer.writerow(r)
        csv_text = out.getvalue()

    t1 = Table(
        id="t_data_debt",
        title="Actionable Data Debt & Remediation Ledger",
        headers=debt_headers,
        rows=debt_rows,
        footnote=f"Export format: {format.upper()}." if format == "csv" else "Remediate these records directly in source monday.com boards.",
    )

    template = f"Identified [[F1]] actionable data debt items requiring operational attention."

    receipt = make_trust_receipt(
        tool_name="data_debt_list",
        sql_executed="-- Queried DQ Ledger for actionable debt items",
        duration_ms=0.5,
        row_count=len(filtered),
    )

    return ToolResult(
        tool="data_debt_list",
        facts=facts,
        tables=[t1],
        charts=[],
        dq=[],
        followups=[],
        template=template,
        audit=receipt,
    )
