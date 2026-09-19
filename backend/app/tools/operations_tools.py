import datetime
from typing import Optional, Dict, Any, List
from app.data.db import db

def get_work_order_health() -> Dict[str, Any]:
    """
    Analyzes operational health of work orders: execution statuses, delayed projects,
    and billing statuses.
    """
    # 1. Execution status breakdown
    status_sql = """
        SELECT
            execution_status,
            COUNT(*) as count,
            COALESCE(SUM(amount_excl_gst), 0) as contracted_value,
            COALESCE(SUM(billed_excl_gst), 0) as billed_value,
            COALESCE(SUM(to_be_billed_excl_gst), 0) as unbilled_value
        FROM work_orders
        GROUP BY execution_status
        ORDER BY count DESC;
    """
    status_rows, dur1, _ = db.query(status_sql)

    # 2. Delayed projects (probable end date in the past and not completed)
    delayed_sql = """
        SELECT
            deal_name,
            client_code,
            serial_no,
            sector,
            execution_status,
            end_date,
            amount_excl_gst,
            to_be_billed_excl_gst
        FROM work_orders
        WHERE end_date IS NOT NULL
          AND end_date < '2026-03-01'
          AND execution_status NOT IN ('Completed', 'Ongoing (Monthly)')
        ORDER BY amount_excl_gst DESC
        LIMIT 10;
    """
    delayed_rows, dur2, _ = db.query(delayed_sql)

    # 3. Billing status breakdown
    billing_sql = """
        SELECT
            billing_status,
            COUNT(*) as count,
            COALESCE(SUM(amount_excl_gst), 0) as contracted_value
        FROM work_orders
        GROUP BY billing_status
        ORDER BY count DESC;
    """
    billing_rows, dur3, _ = db.query(billing_sql)

    return {
        "total_orders": sum(r["count"] for r in status_rows),
        "execution_breakdown": status_rows,
        "delayed_orders_count": len(delayed_rows),
        "delayed_orders_sample": delayed_rows,
        "billing_status_breakdown": billing_rows,
        "audit": {
            "query": status_sql.strip(),
            "duration_ms": round(dur1 + dur2 + dur3, 2),
            "rows_scanned": sum(r["count"] for r in status_rows),
            "rows_matched": sum(r["count"] for r in status_rows),
            "rows_excluded": 0
        }
    }

def get_cross_board_conversion() -> Dict[str, Any]:
    """
    Measures conversion efficiency of Won Deals into operational Work Orders.
    Identifies revenue leakage at the Sales-to-Ops handoff point.
    """
    sql = """
        WITH won_deals AS (
            SELECT
                deal_name,
                join_key,
                deal_value,
                sector,
                owner_code,
                close_date
            FROM deals
            WHERE deal_status = 'Won'
        ),
        linked_wo AS (
            SELECT DISTINCT join_key, 1 as has_wo
            FROM work_orders
        )
        SELECT
            w.deal_name,
            w.sector,
            w.owner_code,
            w.deal_value,
            COALESCE(l.has_wo, 0) as has_wo
        FROM won_deals w
        LEFT JOIN linked_wo l ON w.join_key = l.join_key;
    """
    rows, dur, _ = db.query(sql)

    total_won = len(rows)
    converted = [r for r in rows if r["has_wo"] == 1]
    pending = [r for r in rows if r["has_wo"] == 0]

    conversion_rate = round((len(converted) / total_won * 100), 2) if total_won > 0 else 0.0
    pending_value = sum(r["deal_value"] for r in pending)

    return {
        "total_won_deals": total_won,
        "converted_to_wo_count": len(converted),
        "pending_wo_creation_count": len(pending),
        "conversion_rate_pct": conversion_rate,
        "pending_handoff_deal_value": round(pending_value, 2),
        "top_pending_deals": sorted(pending, key=lambda x: x["deal_value"], reverse=True)[:5],
        "audit": {
            "query": sql.strip(),
            "duration_ms": round(dur, 2),
            "rows_scanned": total_won,
            "rows_matched": total_won,
            "rows_excluded": 0
        }
    }

def get_data_debt_report() -> Dict[str, Any]:
    """
    Produces a ranked data hygiene remediation report across Deals and Work Orders.
    """
    debt_items = []

    # 1. Work Orders with "Update Required"
    ur_sql = """
        SELECT serial_no, deal_name, owner_code, sector, billing_status, amount_excl_gst
        FROM work_orders
        WHERE billing_status = 'Update Required';
    """
    ur_rows, _, _ = db.query(ur_sql)
    for r in ur_rows:
        debt_items.append({
            "id": f"WO-{r.get('serial_no') or r.get('deal_name')}",
            "type": "work_order",
            "entity_name": r.get("deal_name"),
            "owner": r.get("owner_code"),
            "sector": r.get("sector"),
            "issue_category": "Billing Status 'Update Required'",
            "severity": "High",
            "description": f"Order {r.get('serial_no')} flagged with 'Update Required'. Contracted: ₹{r.get('amount_excl_gst', 0):,.2f}",
            "recommended_action": "Verify completed deliverables with ops and generate pending invoice in ERP"
        })

    # 2. Completed Work Orders with 0 billed value
    comp_unbilled_sql = """
        SELECT serial_no, deal_name, owner_code, sector, amount_excl_gst
        FROM work_orders
        WHERE execution_status = 'Completed' AND billed_excl_gst = 0 AND amount_excl_gst > 0;
    """
    cub_rows, _, _ = db.query(comp_unbilled_sql)
    for r in cub_rows:
        debt_items.append({
            "id": f"WO-UNBILLED-{r.get('serial_no')}",
            "type": "work_order",
            "entity_name": r.get("deal_name"),
            "owner": r.get("owner_code"),
            "sector": r.get("sector"),
            "issue_category": "Unbilled Completed Project",
            "severity": "High",
            "description": f"Field execution completed but ₹{r.get('amount_excl_gst', 0):,.2f} remains completely unbilled",
            "recommended_action": "Raise client tax invoice immediately to prevent revenue leakage"
        })

    # 3. Deals with zero or null deal value
    zero_deal_sql = """
        SELECT deal_name, owner_code, sector, deal_stage
        FROM deals
        WHERE deal_value = 0 AND deal_status = 'Open';
    """
    zd_rows, _, _ = db.query(zero_deal_sql)
    for r in zd_rows:
        debt_items.append({
            "id": f"DEAL-ZERO-{r.get('deal_name')}",
            "type": "deal",
            "entity_name": r.get("deal_name"),
            "owner": r.get("owner_code"),
            "sector": r.get("sector"),
            "issue_category": "Missing Deal Value in Pipeline",
            "severity": "Medium",
            "description": f"Open deal in stage '{r.get('deal_stage')}' has ₹0 value recorded",
            "recommended_action": "BD rep must add estimated commercial value based on survey area/deliverables"
        })

    return {
        "total_debt_records": len(debt_items),
        "high_severity_count": len([x for x in debt_items if x["severity"] == "High"]),
        "medium_severity_count": len([x for x in debt_items if x["severity"] == "Medium"]),
        "records": debt_items
    }
