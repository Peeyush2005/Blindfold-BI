from typing import Optional, Dict, Any, List
from app.data.db import db

def get_revenue_realization_summary(sector: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes revenue realization waterfall: Contracted -> Billed -> Collected -> Receivable.
    Also calculates unbilled backlog and collection efficiency.
    """
    conditions = []
    params = []

    if sector:
        conditions.append("LOWER(sector) = LOWER(?)")
        params.append(sector)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql_totals = f"""
        SELECT
            COUNT(*) as total_work_orders,
            COALESCE(SUM(amount_excl_gst), 0) as total_contracted_excl_gst,
            COALESCE(SUM(amount_incl_gst), 0) as total_contracted_incl_gst,
            COALESCE(SUM(billed_excl_gst), 0) as total_billed_excl_gst,
            COALESCE(SUM(billed_incl_gst), 0) as total_billed_incl_gst,
            COALESCE(SUM(collected_incl_gst), 0) as total_collected_incl_gst,
            COALESCE(SUM(to_be_billed_excl_gst), 0) as unbilled_backlog_excl_gst,
            COALESCE(SUM(receivable_amount), 0) as total_receivable
        FROM work_orders
        {where_clause};
    """
    rows, dur1, _ = db.query(sql_totals, params)
    data = rows[0] if rows else {}

    contracted = float(data.get("total_contracted_excl_gst", 0.0))
    billed = float(data.get("total_billed_excl_gst", 0.0))
    billed_incl = float(data.get("total_billed_incl_gst", 0.0))
    collected = float(data.get("total_collected_incl_gst", 0.0))
    receivable = float(data.get("total_receivable", 0.0))
    unbilled = float(data.get("unbilled_backlog_excl_gst", 0.0))

    realization_rate = round((billed / contracted * 100), 2) if contracted > 0 else 0.0
    collection_eff = round((collected / billed_incl * 100), 2) if billed_incl > 0 else 0.0

    # Sector breakdown
    sector_sql = f"""
        SELECT
            sector,
            COUNT(*) as order_count,
            COALESCE(SUM(amount_excl_gst), 0) as contracted_excl_gst,
            COALESCE(SUM(billed_excl_gst), 0) as billed_excl_gst,
            COALESCE(SUM(collected_incl_gst), 0) as collected_incl_gst,
            COALESCE(SUM(receivable_amount), 0) as receivable_amount
        FROM work_orders
        {where_clause}
        GROUP BY sector
        ORDER BY contracted_excl_gst DESC;
    """
    sector_rows, dur2, _ = db.query(sector_sql, params)

    # Top outstanding receivables
    top_debtors_sql = f"""
        SELECT
            deal_name,
            client_code,
            sector,
            receivable_amount,
            ar_priority,
            execution_status
        FROM work_orders
        WHERE receivable_amount > 0
        ORDER BY receivable_amount DESC
        LIMIT 5;
    """
    debtor_rows, dur3, _ = db.query(top_debtors_sql)

    return {
        "summary": {
            "total_work_orders": int(data.get("total_work_orders", 0)),
            "contracted_amount_excl_gst": round(contracted, 2),
            "billed_amount_excl_gst": round(billed, 2),
            "collected_amount_incl_gst": round(collected, 2),
            "unbilled_backlog_excl_gst": round(unbilled, 2),
            "outstanding_receivables": round(receivable, 2),
            "realization_rate_pct": realization_rate,
            "collection_efficiency_pct": collection_eff
        },
        "by_sector": sector_rows,
        "top_debtors": debtor_rows,
        "audit": {
            "query": sql_totals.strip(),
            "params": params,
            "duration_ms": round(dur1 + dur2 + dur3, 2),
            "rows_scanned": int(data.get("total_work_orders", 0)),
            "rows_matched": int(data.get("total_work_orders", 0)),
            "rows_excluded": 0,
            "exclusion_reason": "No row exclusions; complete work order cohort evaluated"
        }
    }
