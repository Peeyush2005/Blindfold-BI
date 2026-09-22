"""
Read-only data snapshot refresh endpoint for Blindfold BI API v1.
Requires X-API-Key and per-IP rate limiting.
Strictly read-only; zero write operations against source boards.
"""

from fastapi import APIRouter, Depends, Request
from app.data.adapter import adapter
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.api.v1.deps import require_api_key, check_rate_limit

router = APIRouter(prefix="/data", tags=["Data Sync v1"])


@router.post(
    "/refresh",
    summary="Trigger Read-Only Data Refresh",
    description="Synchronously reload read-only snapshot data into DuckDB and rebuild gateway surrogate catalogs. Enforces strict read-only governance.",
    dependencies=[Depends(check_rate_limit), Depends(require_api_key("data:refresh"))],
    responses={
        200: {"description": "Data snapshot refreshed successfully."},
        401: {"description": "Unauthorized - invalid or missing X-API-Key."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def refresh_data_endpoint():
    status = await adapter.refresh(force=True)
    ok = bool(status.get("connected"))
    return {
        "status": "success" if ok else "failed",
        "message": (
            "Re-read both boards from monday.com (read-only)."
            if ok else f"Refresh did not reach monday.com: {status.get('error')}"
        ),
        "details": {k: v for k, v in status.items() if k != "stats"},
    }
