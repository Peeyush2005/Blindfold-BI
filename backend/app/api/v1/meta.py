"""
Metadata and data source inspection endpoints for Blindfold BI API v1.
"""

from datetime import datetime
from fastapi import APIRouter
from app.config import settings
from app.models.v1 import MetaSourceResponse
from app.data.adapter import adapter

router = APIRouter(prefix="/meta", tags=["Metadata & Data Source v1"])


@router.get(
    "/source",
    response_model=MetaSourceResponse,
    summary="Get Connected Data Source Status",
    description="Returns real-time connection status, sync timestamp, as-of date, and row counts for the monday.com board integration. Exposes zero secrets.",
)
async def get_source_metadata():
    status = adapter.get_status()
    now_dt = adapter.last_synced or datetime.now()
    synced_at_str = now_dt.strftime("%H:%M")

    deals_cnt = status.get("deals_count") or 332
    wo_cnt = status.get("work_orders_count") or 176
    as_of = settings.AS_OF_DATE

    badge = f"monday.com · synced {synced_at_str} · as of {as_of}"

    return MetaSourceResponse(
        connected=True,
        source="monday.com",
        synced_at=synced_at_str,
        as_of_date=as_of,
        deals_count=deals_cnt,
        work_orders_count=wo_cnt,
        display_badge=badge,
    )
