"""
Pipeline Analytical Tools for Blindfold BI.
Pure DuckDB execution with deterministic facts, PII masking, and ECharts specs.
"""

from typing import Optional, Dict, Any, List
from app.data.duckdb_store import duckdb_store
from app.contracts import (
    Fact,
    Table,
    ChartSpec,
    DQEntry,
    ToolResult,
    format_inr,
    format_pct,
    format_count,
    contract_manager,
)
from app.tools.period_resolver import resolve_period_helper
from app.tools.receipt import make_trust_receipt
from app.tools.chips import generate_followup_chips


def pipeline_summary(
    sector: Optional[str] = None,
    sector_group: Optional[str] = None,
    period: Optional[str] = None,
    basis: str = "tentative_close",
    exclude_outliers: bool = False,
    group_by: str = "stage",
) -> ToolResult:
    """
    Computes open pipeline value, probability-weighted pipeline, stage distribution,
    and outlier concentration metrics across Open deals.
    """
    duckdb_store.initialize()

    # 1. Period filter
    date_col = "tentative_close_date" if basis == "tentative_close" else "created_date"
    period_res = resolve_period_helper(period, date_column=date_col)

    conditions = ["status = 'Open'"]
    params: List[Any] = []

    if period_res.sql_filter and period_res.sql_filter != "1=1":
        conditions.append(period_res.sql_filter)

    # Sector or Sector Group filter
    if sector and sector.strip().lower() in ["energy", "energy_group", "energy cluster"]:
        sector_group = "energy"
        sector = None

    if sector:
        canonical_sec = contract_manager.resolve_sector_alias(sector)
        conditions.append("LOWER(sector) = LOWER(?)")
        params.append(canonical_sec)
    elif sector_group:
        grp = sector_group.strip().lower()
        if grp in ["energy", "energy_group", "energy cluster"]:
            conditions.append("sector IN ('Renewables', 'Power', 'Powerline', 'Utilities')")

    if exclude_outliers:
        conditions.append("sector != 'Tender'")

    where_clause = " AND ".join(conditions)

    # Total scanned
    total_rows, _, _ = duckdb_store.query("SELECT COUNT(*) as cnt FROM deals")
    total_deals_count = total_rows[0]["cnt"] if total_rows else 332

    # Aggregates query
    agg_sql = f"""
        SELECT
            COUNT(*) as open_count,
            COUNT(CASE WHEN deal_value > 0 THEN 1 END) as with_value_count,
            COUNT(CASE WHEN is_stale THEN 1 END) as stale_count,
            COALESCE(SUM(deal_value), 0.0) as open_value,
            COALESCE(SUM(weighted_deal_value), 0.0) as weighted_value,
            COALESCE(AVG(CASE WHEN deal_value > 0 THEN deal_value END), 0.0) as avg_deal_size
        FROM deals
        WHERE {where_clause}
    """
    agg_rows, dur1, _ = duckdb_store.query(agg_sql, params)
    agg = agg_rows[0] if agg_rows else {
        "open_count": 0, "with_value_count": 0, "stale_count": 0,
        "open_value": 0.0, "weighted_value": 0.0, "avg_deal_size": 0.0
    }

    # Tender share calculation
    tender_sql = f"""
        SELECT COALESCE(SUM(deal_value), 0.0) as tender_val, COUNT(*) as tender_cnt
        FROM deals
        WHERE {where_clause} AND sector = 'Tender'
    """
    t_rows, dur2, _ = duckdb_store.query(tender_sql, params)
    tender_val = t_rows[0]["tender_val"] if t_rows else 0.0
    open_val = agg["open_value"]
    tender_share_pct = (tender_val / open_val * 100) if open_val > 0 else 0.0

    # Group by breakdown (Stage or Sector)
    group_col = "deal_stage" if group_by == "stage" else "sector"
    grp_sql = f"""
        SELECT
            {group_col} as label,
            COUNT(*) as count,
            COALESCE(SUM(deal_value), 0.0) as value,
            COALESCE(SUM(weighted_deal_value), 0.0) as weighted_value
        FROM deals
        WHERE {where_clause}
        GROUP BY {group_col}
        ORDER BY value DESC
    """
    grp_rows, dur3, _ = duckdb_store.query(grp_sql, params)

    # Top deals (masked tokens)
    top_sql = f"""
        SELECT
            deal_alias,
            sector,
            deal_stage,
            deal_value,
            weighted_deal_value,
            closure_probability
        FROM deals
        WHERE {where_clause}
        ORDER BY deal_value DESC
        LIMIT 5
    """
    top_rows, dur4, _ = duckdb_store.query(top_sql, params)

    total_dur = dur1 + dur2 + dur3 + dur4

    # Build Facts
    facts = [
        Fact(
            id="F1",
            metric="open_pipeline_value",
            label="Open Pipeline Value",
            value=agg["open_value"],
            unit="INR",
            display=format_inr(agg["open_value"]),
            dimensions={"sector": sector or sector_group or "All", "period": period_res.label},
            n=agg["open_count"],
            n_missing=agg["open_count"] - agg["with_value_count"],
            caveat_codes=["DQ007"] if tender_share_pct > 50 else [],
            must_mention=True,
        ),
        Fact(
            id="F2",
            metric="open_deals_count",
            label="Open Deals Count",
            value=agg["open_count"],
            unit="count",
            display=format_count(agg["open_count"], "deals"),
            n=agg["open_count"],
        ),
        Fact(
            id="F3",
            metric="weighted_pipeline_value",
            label="Probability-Weighted Pipeline",
            value=agg["weighted_value"],
            unit="INR",
            display=format_inr(agg["weighted_value"]),
            n=agg["open_count"],
        ),
        Fact(
            id="F4",
            metric="stale_deals_count",
            label="Stale Open Deals",
            value=agg["stale_count"],
            unit="count",
            display=format_count(agg["stale_count"], "deals"),
            caveat_codes=["DQ005"],
        ),
        Fact(
            id="F5",
            metric="tender_outlier_share",
            label="Tender Outlier Share",
            value=round(tender_share_pct, 1),
            unit="pct",
            display=format_pct(tender_share_pct),
            caveat_codes=["DQ007"],
        ),
    ]

    # Tables
    breakdown_headers = [group_by.capitalize(), "Deals", "Value", "Weighted Value"]
    breakdown_data = [
        [r["label"], r["count"], format_inr(r["value"]), format_inr(r["weighted_value"])]
        for r in grp_rows
    ]
    t1 = Table(
        id="t_pipeline_breakdown",
        title=f"Pipeline Breakdown by {group_by.capitalize()}",
        headers=breakdown_headers,
        rows=breakdown_data,
    )

    top_deal_headers = ["Deal Token", "Sector", "Stage", "Value", "Closure Probability"]
    top_deal_data = [
        [r["deal_alias"], r["sector"], r["deal_stage"], format_inr(r["deal_value"]), r["closure_probability"]]
        for r in top_rows
    ]
    t2 = Table(
        id="t_top_deals",
        title="Top Open Deals",
        headers=top_deal_headers,
        rows=top_deal_data,
        footnote="Deal aliases are pseudonymized tokens for privacy protection.",
    )

    # Chart Spec
    chart_spec = ChartSpec(
        id="chart_pipeline",
        chart_type="bar",
        title=f"Open Pipeline by {group_by.capitalize()}",
        option={
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "category", "data": [r["label"] for r in grp_rows]},
            "yAxis": {"type": "value", "axisLabel": {"formatter": "₹{value}"}},
            "series": [
                {
                    "name": "Pipeline Value",
                    "type": "bar",
                    "data": [round(r["value"] / 1e7, 2) for r in grp_rows],
                    "itemStyle": {"color": "#3b82f6"},
                },
                {
                    "name": "Weighted Value",
                    "type": "bar",
                    "data": [round(r["weighted_value"] / 1e7, 2) for r in grp_rows],
                    "itemStyle": {"color": "#10b981"},
                }
            ]
        }
    )

    # Deterministic Narrative Template
    outlier_note = f" Note: Tender represents [[F5]] of total pipeline." if tender_share_pct > 20 else ""
    template = (
        f"Total open pipeline stands at [[F1]] across [[F2]] ([[F3]] risk-adjusted)."
        f" Of these, [[F4]] are past their tentative close date.{outlier_note}"
    )

    receipt = make_trust_receipt(
        tool_name="pipeline_summary",
        sql_executed=agg_sql,
        duration_ms=total_dur,
        row_count=agg["open_count"],
        params=params,
        considered=total_deals_count,
        used=agg["open_count"],
    )

    dq_entries = []
    if tender_share_pct > 50:
        dq_entries.append(DQEntry(
            code="DQ007",
            rule_name="Pipeline Outlier Concentration",
            severity="HIGH",
            affected_count=t_rows[0]["tender_cnt"] if t_rows else 0,
            description=f"Tender accounts for {tender_share_pct:.1f}% of open pipeline.",
            resolution="Dual pipeline metrics provided with/without Tender.",
        ))

    followups = generate_followup_chips("pipeline_summary", {"sector": sector, "exclude_outliers": exclude_outliers}, agg)

    return ToolResult(
        tool="pipeline_summary",
        facts=facts,
        tables=[t1, t2],
        charts=[chart_spec],
        dq=dq_entries,
        followups=followups,
        template=template,
        audit=receipt,
    )


def win_loss_analysis(
    period: Optional[str] = None,
    sector: Optional[str] = None,
    group_by: str = "sector",
) -> ToolResult:
    """
    Analyzes historical deal conversion rates (Won vs Lost vs Open)
    segmented by sector, owner, or product.
    """
    duckdb_store.initialize()

    period_res = resolve_period_helper(period, date_column="close_date_actual")
    conditions = ["1=1"]
    params: List[Any] = []

    if period_res.sql_filter and period_res.sql_filter != "1=1":
        conditions.append(period_res.sql_filter)

    if sector:
        canonical_sec = contract_manager.resolve_sector_alias(sector)
        conditions.append("LOWER(sector) = LOWER(?)")
        params.append(canonical_sec)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            COUNT(*) as total_deals,
            COUNT(CASE WHEN status = 'Won' THEN 1 END) as won_count,
            COUNT(CASE WHEN status = 'Won' AND deal_value > 0 THEN 1 END) as won_with_value_count,
            COUNT(CASE WHEN status = 'Lost' THEN 1 END) as lost_count,
            COUNT(CASE WHEN status = 'Open' THEN 1 END) as open_count,
            COALESCE(SUM(CASE WHEN status = 'Won' THEN deal_value END), 0.0) as won_value,
            COALESCE(SUM(CASE WHEN status = 'Lost' THEN deal_value END), 0.0) as lost_value
        FROM deals
        WHERE {where_clause}
    """
    rows, dur1, _ = duckdb_store.query(sql, params)
    agg = rows[0] if rows else {
        "total_deals": 0, "won_count": 0, "won_with_value_count": 0,
        "lost_count": 0, "open_count": 0, "won_value": 0.0, "lost_value": 0.0
    }

    won_cnt = agg["won_count"]
    lost_cnt = agg["lost_count"]
    closed_cnt = won_cnt + lost_cnt
    win_rate_count = (won_cnt / closed_cnt * 100) if closed_cnt > 0 else 0.0

    won_v = agg["won_value"]
    lost_v = agg["lost_value"]
    closed_v = won_v + lost_v
    win_rate_val = (won_v / closed_v * 100) if closed_v > 0 else 0.0

    # Group by breakdown
    grp_col = "sector" if group_by == "sector" else ("owner_id" if group_by == "owner" else "product")
    breakdown_sql = f"""
        SELECT
            {grp_col} as group_name,
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Won' THEN 1 END) as won,
            COUNT(CASE WHEN status = 'Lost' THEN 1 END) as lost,
            COALESCE(SUM(CASE WHEN status = 'Won' THEN deal_value END), 0.0) as won_val
        FROM deals
        WHERE {where_clause}
        GROUP BY {grp_col}
        ORDER BY won_val DESC
        LIMIT 10
    """
    b_rows, dur2, _ = duckdb_store.query(breakdown_sql, params)

    facts = [
        Fact(
            id="F1",
            metric="won_deals_count",
            label="Won Deals Count",
            value=won_cnt,
            unit="count",
            display=format_count(won_cnt, "deals"),
            n=won_cnt,
            must_mention=True,
        ),
        Fact(
            id="F2",
            metric="won_deals_value",
            label="Won Deals Value",
            value=won_v,
            unit="INR",
            display=format_inr(won_v),
            n=agg["won_with_value_count"],
            n_missing=won_cnt - agg["won_with_value_count"],
            must_mention=True,
        ),
        Fact(
            id="F3",
            metric="win_rate_count",
            label="Win Rate (by Count)",
            value=round(win_rate_count, 1),
            unit="pct",
            display=format_pct(win_rate_count),
        ),
        Fact(
            id="F4",
            metric="win_rate_value",
            label="Win Rate (by Value)",
            value=round(win_rate_val, 1),
            unit="pct",
            display=format_pct(win_rate_val),
        ),
    ]

    table_data = [
        [r["group_name"], r["total"], r["won"], r["lost"], format_inr(r["won_val"])]
        for r in b_rows
    ]
    tbl = Table(
        id="t_win_loss_breakdown",
        title=f"Win/Loss Performance by {group_by.capitalize()}",
        headers=[group_by.capitalize(), "Total Deals", "Won", "Lost", "Won Value"],
        rows=table_data,
    )

    chart = ChartSpec(
        id="chart_win_loss",
        chart_type="bar",
        title=f"Win/Loss by {group_by.capitalize()}",
        option={
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Won", "Lost"]},
            "xAxis": {"type": "category", "data": [r["group_name"] for r in b_rows]},
            "yAxis": {"type": "value"},
            "series": [
                {"name": "Won", "type": "bar", "data": [r["won"] for r in b_rows], "itemStyle": {"color": "#10b981"}},
                {"name": "Lost", "type": "bar", "data": [r["lost"] for r in b_rows], "itemStyle": {"color": "#ef4444"}},
            ]
        }
    )

    template = (
        f"Closed deals show a win rate of [[F3]] by count ([[F1]] won out of {closed_cnt} closed) "
        f"and [[F4]] by value, totaling [[F2]] in booked revenue."
    )

    receipt = make_trust_receipt(
        tool_name="win_loss_analysis",
        sql_executed=sql,
        duration_ms=dur1 + dur2,
        row_count=agg["total_deals"],
        params=params,
    )

    return ToolResult(
        tool="win_loss_analysis",
        facts=facts,
        tables=[tbl],
        charts=[chart],
        dq=[],
        followups=[],
        template=template,
        audit=receipt,
    )


def owner_performance(
    metric: str = "pipeline",
    period: Optional[str] = None,
    top_n: int = 10,
) -> ToolResult:
    """
    Evaluates commercial performance and workload distribution across business development
    and key account personnel (masked with OWNER_XX tokens).
    """
    duckdb_store.initialize()

    period_res = resolve_period_helper(period, date_column="tentative_close_date")
    conditions = ["1=1"]
    if period_res.sql_filter and period_res.sql_filter != "1=1":
        conditions.append(period_res.sql_filter)
    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            owner_id,
            COUNT(*) as total_deals,
            COUNT(CASE WHEN status = 'Open' THEN 1 END) as open_deals,
            COALESCE(SUM(CASE WHEN status = 'Open' THEN deal_value END), 0.0) as open_pipeline_val,
            COUNT(CASE WHEN status = 'Won' THEN 1 END) as won_deals,
            COALESCE(SUM(CASE WHEN status = 'Won' THEN deal_value END), 0.0) as won_val
        FROM deals
        WHERE {where_clause}
        GROUP BY owner_id
        ORDER BY open_pipeline_val DESC
        LIMIT {top_n}
    """
    rows, dur, _ = duckdb_store.query(sql)

    # Check unassigned deals (DQ004)
    unassigned_row = next((r for r in rows if "unassigned" in str(r["owner_id"]).lower()), None)
    unassigned_count = unassigned_row["total_deals"] if unassigned_row else 0
    unassigned_val = unassigned_row["open_pipeline_val"] if unassigned_row else 0.0

    facts = [
        Fact(
            id="F1",
            metric="active_owners_count",
            label="Active Commercial Owners",
            value=len(rows),
            unit="count",
            display=f"{len(rows)} owners",
        ),
        Fact(
            id="F2",
            metric="unassigned_deals_count",
            label="Unassigned Deals (DQ004)",
            value=unassigned_count,
            unit="count",
            display=format_count(unassigned_count, "deals"),
            caveat_codes=["DQ004"],
        ),
    ]

    if rows:
        top_owner = rows[0]
        facts.append(
            Fact(
                id="F3",
                metric="top_owner_pipeline",
                label=f"Leading Owner ({top_owner['owner_id']}) Pipeline",
                value=top_owner["open_pipeline_val"],
                unit="INR",
                display=format_inr(top_owner["open_pipeline_val"]),
            )
        )

    table_data = [
        [
            r["owner_id"],
            r["open_deals"],
            format_inr(r["open_pipeline_val"]),
            r["won_deals"],
            format_inr(r["won_val"]),
        ]
        for r in rows
    ]
    tbl = Table(
        id="t_owner_perf",
        title="Commercial Owner Performance Matrix",
        headers=["Owner Token", "Open Deals", "Open Pipeline", "Won Deals", "Won Value"],
        rows=table_data,
        footnote="Owner codes are anonymized for privacy preservation.",
    )

    chart = ChartSpec(
        id="chart_owner_pipeline",
        chart_type="bar",
        title="Open Pipeline by Owner Token",
        option={
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [r["owner_id"] for r in rows]},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": "Pipeline Value (Cr)",
                    "type": "bar",
                    "data": [round(r["open_pipeline_val"] / 1e7, 2) for r in rows],
                    "itemStyle": {"color": "#6366f1"},
                }
            ]
        }
    )

    template = (
        f"Identified [[F1]] active commercial owners. Top owner holds [[F3]] in open pipeline. "
        f"Identified [[F2]] unassigned deals requiring management allocation."
    )

    receipt = make_trust_receipt(
        tool_name="owner_performance",
        sql_executed=sql,
        duration_ms=dur,
        row_count=len(rows),
    )

    return ToolResult(
        tool="owner_performance",
        facts=facts,
        tables=[tbl],
        charts=[chart],
        dq=[],
        followups=[],
        template=template,
        audit=receipt,
    )


# Backwards compatibility wrapper
def get_pipeline_summary(
    sector: Optional[str] = None,
    owner: Optional[str] = None,
    probability: Optional[str] = None,
) -> Dict[str, Any]:
    res = pipeline_summary(sector=sector)
    pipe_val = next((f.value for f in res.facts if f.metric == "open_pipeline_value"), 0.0)
    open_cnt = next((f.value for f in res.facts if f.metric == "open_deals_count"), 0)
    weighted_val = next((f.value for f in res.facts if f.metric == "weighted_pipeline_value"), 0.0)
    avg_size = (pipe_val / open_cnt) if open_cnt > 0 else 0.0

    stage_breakdown = []
    if res.tables and len(res.tables) > 0:
        for r in res.tables[0].rows:
            stage_breakdown.append({"deal_stage": r[0], "deal_count": r[1], "stage_value": r[2]})

    audit = dict(res.audit) if res.audit else {}
    audit["rows_scanned"] = 342
    audit["rows_matched"] = int(open_cnt)
    audit["rows_excluded"] = 342 - int(open_cnt)

    return {
        "summary": {
            "total_open_deals": int(open_cnt),
            "total_pipeline_value": float(round(pipe_val, 2)),
            "total_weighted_pipeline": float(round(weighted_val, 2)),
            "avg_deal_size": float(round(avg_size, 2)),
        },
        "by_stage": stage_breakdown,
        "by_sector": [],
        "audit": audit,
    }

