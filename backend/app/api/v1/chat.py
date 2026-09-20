"""
Real-time SSE Streaming Chat Endpoint for Blindfold BI API v1.
Emits typed SSE events: run.started, stage, tool, llm, answer, run.finished / run.error
Flushes 15s keepalive comments (: keepalive\\n\\n) when idle.
"""

import json
import asyncio
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.models.v1 import ChatRequestV1
from app.core.orchestrator import orchestrator
from app.api.v1.deps import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Conversational BI v1"])


async def sse_event_generator(
    question: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Yields Server-Sent Events formatted as:
    event: <event_name>
    data: <json_data>

    Emits ': keepalive\\n\\n' every 15 seconds while waiting for the next event.
    """
    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(
        orchestrator.stream_pipeline(
            question=question,
            session_id=session_id,
            queue=queue,
        )
    )

    try:
        while True:
            try:
                # Wait up to 15 seconds for next event
                item = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Emit keepalive comment if waiting longer than 15s
                yield ": keepalive\n\n"
                continue

            if item is None:
                # Sentinel indicating end of stream
                break

            event_type = item.get("event", "message")
            event_data = item.get("data", {})
            payload_str = json.dumps(event_data)
            yield f"event: {event_type}\ndata: {payload_str}\n\n"

    except asyncio.CancelledError:
        logger.info(f"SSE client disconnected for session {session_id}")
        task.cancel()
        raise
    except Exception as e:
        logger.error(f"Error in SSE event stream: {e}", exc_info=True)
        err_data = json.dumps({"code": "STREAM_EXCEPTION", "message": str(e), "retryable": False})
        yield f"event: run.error\ndata: {err_data}\n\n"
    finally:
        if not task.done():
            task.cancel()


@router.post(
    "/chat",
    summary="Streaming Conversational BI Chat Orchestrator",
    description="Stream 8-stage analytical pipeline execution events in real time via Server-Sent Events (SSE).",
    response_class=StreamingResponse,
    dependencies=[Depends(check_rate_limit)],
    responses={
        200: {
            "description": "Server-Sent Events stream emitting run.started, stage, tool, llm, answer, and run.finished events.",
            "content": {"text/event-stream": {}},
        },
        429: {"description": "Per-IP rate limit exceeded (Problem+JSON)."},
    },
)
async def chat_endpoint(payload: ChatRequestV1, request: Request):
    """
    Accepts question or suggestion chip selection and initiates the 8-stage analytical pipeline.
    """
    query = (payload.question or payload.chip or "").strip()
    session_id = payload.session_id or "default-session"

    return StreamingResponse(
        sse_event_generator(question=query, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
