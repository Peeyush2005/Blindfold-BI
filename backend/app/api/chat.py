"""
Chat and Pipeline Simulation SSE API endpoints.
Provides standard synchronous chat execution and real-time Server-Sent Events (SSE)
streaming of the S1-S10 pipeline state machine.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.core.orchestrator import orchestrator
from app.events.bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat & Pipeline Simulation"])


@router.post("", response_model=ChatResponse)
async def execute_chat(request: ChatRequest):
    """
    Executes the S1-S10 state machine and returns the full structured ChatResponse
    including trust receipt, verified prose, suggestion chips, and pipeline trace.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty")

    session_id = request.session_id or "default-session"
    try:
        response = await orchestrator.execute_query(request.message, session_id=session_id)
        return response
    except Exception as e:
        logger.error(f"Error executing chat pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/stream")
async def stream_pipeline_events(session_id: str = Query("default-session", description="Session ID to listen to")):
    """
    SSE stream endpoint. Clients connect via EventSource with session_id to receive
    live S1-S10 step events and token updates during query execution.
    """
    return StreamingResponse(
        event_bus.stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/stream")
async def execute_and_stream_pipeline(request: ChatRequest):
    """
    Executes a query and streams real-time S1-S10 state machine step transitions
    and final completion payload over SSE.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty")

    session_id = request.session_id or f"sess_{int(asyncio.get_event_loop().time() * 1000)}"

    # Pre-create the queue so events from S1 are never missed
    q = await event_bus.create_channel(session_id)

    # Launch pipeline execution in background
    async def _runner():
        try:
            await orchestrator.execute_query(request.message, session_id=session_id)
        except Exception as e:
            logger.error(f"Error in streaming pipeline execution: {e}", exc_info=True)
            await event_bus.emit_error(session_id, str(e))

    asyncio.create_task(_runner())

    async def _event_generator():
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                if hasattr(item, "to_sse"):
                    yield item.to_sse()
                elif isinstance(item, dict):
                    import json
                    evt_type = item.get("event", "message")
                    data_str = json.dumps(item.get("data", {}))
                    yield f"event: {evt_type}\ndata: {data_str}\n\n"
        finally:
            await event_bus.remove_channel(session_id)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
