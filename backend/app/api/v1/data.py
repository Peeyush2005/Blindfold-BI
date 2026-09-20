"""
Read-only data snapshot refresh endpoint for Blindfold BI API v1.
Requires X-API-Key and per-IP rate limiting.
Strictly read-only; zero write operations against source boards.
"""

from fastapi import APIRouter, Depends, Request
from app.data.adapter import adapter
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.api.v1.deps import verify_api_key, check_rate_limit

router = APIRouter(prefix="/data", tags=["Data Sync v1"])


@router.post(
    "/refresh",
    summary="Trigger Read-Only Data Refresh",
    description="Synchronously reload read-only snapshot data into DuckDB and rebuild gateway surrogate catalogs. Enforces strict read-only governance.",
    dependencies=[Depends(check_rate_limit), Depends(verify_api_key)],
    responses={
        200: {"description": "Data snapshot refreshed successfully."},
        401: {"description": "Unauthorized - invalid or missing X-API-Key."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def refresh_data_endpoint():
    db.init_db(force_refresh=True)
    orchestrator.init_catalog()
    status = adapter.get_status()
    return {
        "status": "success",
        "message": "Data snapshot refreshed into DuckDB in read-only mode.",
        "details": status,
    }
