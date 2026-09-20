"""
Run inspection, replay, and history lookup endpoint for Blindfold BI API v1.
"""

from typing import List
from fastapi import APIRouter, Request, status
from app.models.v1 import RunRecord
from app.core.run_store import run_store
from app.api.v1.deps import ProblemException

router = APIRouter(prefix="/runs", tags=["Run Inspection & Replay v1"])


@router.get(
    "/{run_id}",
    response_model=RunRecord,
    summary="Inspect or Replay an Analytical Run",
    description="Fetch the complete state, stages, tool events, and generated answer blocks of a completed or historical run.",
    responses={
        200: {"description": "Full run record containing stages, events, and answer."},
        404: {"description": "Run record not found."},
    },
)
async def get_run_by_id(run_id: str, request: Request):
    record = run_store.get_run(run_id)
    if not record:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Run Not Found",
            detail=f"Analytical run '{run_id}' was not found in active memory history.",
            code="RUN_NOT_FOUND",
            instance=request.url.path,
        )
    return record


@router.get(
    "",
    response_model=List[RunRecord],
    summary="List Recent Analytical Runs",
    description="Retrieve the list of recent pipeline runs executed during this session.",
)
async def list_recent_runs(limit: int = 20):
    return run_store.list_recent(limit=limit)
