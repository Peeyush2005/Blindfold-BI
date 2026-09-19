import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from app.config import settings
from app.integrations.monday_client import monday_client
from app.data.adapter import adapter
from app.data.db import db
from app.tools.operations_tools import get_data_debt_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monday", tags=["Monday.com Integration"])

class MondayConfigUpdate(BaseModel):
    api_token: Optional[str] = None
    deals_board_id: Optional[str] = None
    wo_board_id: Optional[str] = None

@router.get("/status")
async def get_monday_status():
    """Get current Monday.com connection status, configured board IDs, and sync metrics."""
    conn_info = await monday_client.test_connection()
    data_status = adapter.get_status()

    # Mask token for security
    token = monday_client.api_token
    masked_token = f"{token[:4]}...{token[-4:]}" if token and len(token) > 8 else ("Configured" if token else "Not Set")

    return {
        "status": "connected" if conn_info.get("connected") else "disconnected",
        "api_configured": monday_client.is_configured,
        "token_preview": masked_token,
        "boards": {
            "deals_board_id": monday_client.deals_board_id or "Not Configured",
            "wo_board_id": monday_client.wo_board_id or "Not Configured",
        },
        "connection_details": conn_info,
        "data_snapshot": data_status,
        "webhook_url": "/api/monday/webhook",
        "supported_events": ["create_item", "change_column_value", "delete_item"]
    }

@router.post("/configure")
async def update_monday_config(config: MondayConfigUpdate):
    """Update runtime Monday.com connection credentials and board IDs."""
    if config.api_token is not None:
        monday_client.api_token = config.api_token.strip()
    if config.deals_board_id is not None:
        monday_client.deals_board_id = config.deals_board_id.strip()
    if config.wo_board_id is not None:
        monday_client.wo_board_id = config.wo_board_id.strip()

    conn_info = await monday_client.test_connection()
    return {
        "status": "updated",
        "connection": conn_info
    }

@router.post("/sync")
async def trigger_monday_sync():
    """Trigger manual data synchronization from Monday.com boards into DuckDB engine."""
    try:
        deals_df, wo_df = adapter.load_data(force_refresh=True)
        # Re-initialize DuckDB with refreshed data
        db.init_db(force_refresh=True)
        return {
            "status": "success",
            "message": "Datasets synchronized and DuckDB re-indexed successfully.",
            "data_source": adapter.source,
            "deals_synced": len(deals_df),
            "work_orders_synced": len(wo_df),
            "last_synced": adapter.last_synced.isoformat() if adapter.last_synced else None
        }
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.post("/push-debt-alerts")
async def push_data_debt_alerts():
    """
    Push detected CRM debt and operational hygiene anomalies back to Monday.com items as alerts.
    """
    try:
        report = get_data_debt_report()
        records = report.get("records", [])
        result = await monday_client.push_data_debt_alerts(records)
        return {
            "status": "success",
            "summary": result,
            "message": f"Processed {result.get('alerts_processed', 0)} alerts for Monday.com boards."
        }
    except Exception as e:
        logger.error(f"Failed to push debt alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Push failed: {str(e)}")

@router.post("/webhook")
async def monday_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Monday.com Webhook receiver.
    1. Responds to Monday.com challenge verification handshake: {"challenge": "..."}
    2. Handles board change events (create_item, change_column_value) and enqueues sync.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Monday.com challenge handshake
    if "challenge" in payload:
        logger.info(f"Monday.com webhook challenge received: {payload['challenge']}")
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})
    event_type = event.get("type", "unknown")
    item_id = event.get("itemId")
    board_id = event.get("boardId")
    logger.info(f"Monday webhook event received: type={event_type}, boardId={board_id}, itemId={item_id}")

    # Enqueue background refresh on board mutations
    if event_type in ["create_item", "change_column_value", "delete_item"]:
        background_tasks.add_task(trigger_monday_sync)

    return {
        "status": "received",
        "event_type": event_type,
        "processed": True
    }
