from typing import Optional, Dict, Any, List
from app.data.db import db

def get_pipeline_summary(sector: Optional[str] = None, owner: Optional[str] = None, probability: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes open pipeline value, probability-weighted pipeline, and stage/sector distribution.
    Executes pure deterministic SQL in DuckDB.
    """
    conditions = ["deal_status = 'Open'"]
    params = []

    if sector:
        conditions.append("LOWER(sector) = LOWER(?)")
        params.append(sector)
    if owner:
        conditions.append("LOWER(owner_code) = LOWER(?)")
        params.append(owner)
    if probability:
        conditions.append("LOWER(closure_probability) = LOWER(?)")
        params.append(probability)

    where_clause = " AND ".join(conditions)

    # 1. Aggregates
    agg_sql = f"""
        SELECT
            COUNT(*) as total_open_deals,
            COALESCE(SUM(deal_value), 0) as total_pipeline_value,
            COALESCE(SUM(weighted_deal_value), 0) as total_weighted_pipeline,
            COALESCE(AVG(deal_value), 0) as avg_deal_size
        FROM deals
        WHERE {where_clause};
    """
    agg_rows, dur1, _ = db.query(agg_sql, params)
    agg_data = agg_rows[0] if agg_rows else {"total_open_deals": 0, "total_pipeline_value": 0, "total_weighted_pipeline": 0, "avg_deal_size": 0}

    # 2. Breakdown by Stage
    stage_sql = f"""
        SELECT
            deal_stage,
            COUNT(*) as deal_count,
            COALESCE(SUM(deal_value), 0) as stage_value
        FROM deals
        WHERE {where_clause}
        GROUP BY deal_stage
        ORDER BY stage_value DESC;
    """
    stage_rows, dur2, _ = db.query(stage_sql, params)

    # 3. Breakdown by Sector
    sector_sql = f"""
        SELECT
            sector,
            COUNT(*) as deal_count,
            COALESCE(SUM(deal_value), 0) as sector_value,
            COALESCE(SUM(weighted_deal_value), 0) as weighted_value
        FROM deals
        WHERE {where_clause}
        GROUP BY sector
        ORDER BY sector_value DESC;
    """
    sector_rows, dur3, _ = db.query(sector_sql, params)

    # 4. Filter provenance (for Trust Receipt)
    total_deals_rows, _, _ = db.query("SELECT COUNT(*) as total FROM deals;")
    total_deals = total_deals_rows[0]["total"]
    rows_scanned = total_deals
    rows_matched = agg_data["total_open_deals"]
    rows_excluded = total_deals - rows_matched

    return {
        "summary": {
            "total_open_deals": int(agg_data["total_open_deals"]),
            "total_pipeline_value": float(round(agg_data["total_pipeline_value"], 2)),
            "total_weighted_pipeline": float(round(agg_data["total_weighted_pipeline"], 2)),
            "avg_deal_size": float(round(agg_data["avg_deal_size"], 2)),
        },
        "by_stage": stage_rows,
        "by_sector": sector_rows,
        "audit": {
            "query": agg_sql.strip(),
            "params": params,
            "duration_ms": round(dur1 + dur2 + dur3, 2),
            "rows_scanned": rows_scanned,
            "rows_matched": rows_matched,
            "rows_excluded": rows_excluded,
            "exclusion_reason": f"Excluded non-Open deals (Won, Dead, On Hold) or deals outside filters: {params}"
        }
    }
