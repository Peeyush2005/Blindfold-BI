"""
Event Bus for Blindfold BI Pipeline Simulation.
Enables real-time Server-Sent Events (SSE) streaming of the S1-S10 state machine
transitions to the UI pipeline theater graph.
"""

import time
import json
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class StepEvent:
    step_id: str          # "S1" through "S10"
    step_name: str        # e.g. "S1: Intake & Normalization"
    status: str           # "running", "completed", "warning", "failed"
    duration_ms: float
    summary: str
    details: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_sse(self) -> str:
        payload = json.dumps(self.to_dict())
        return f"event: step\ndata: {payload}\n\n"


class PipelineEventBus:
    """
    In-memory async queue event bus supporting multiple concurrent SSE subscribers.
    Each query run gets its own channel/queue for isolated event streaming.
    """

    def __init__(self):
        self._channels: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def create_channel(self, session_id: str) -> asyncio.Queue:
        async with self._lock:
            q = asyncio.Queue()
            self._channels[session_id] = q
            return q

    async def remove_channel(self, session_id: str) -> None:
        async with self._lock:
            if session_id in self._channels:
                del self._channels[session_id]

    async def emit_step(
        self,
        session_id: str,
        step_id: str,
        step_name: str,
        status: str,
        duration_ms: float,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = StepEvent(
            step_id=step_id,
            step_name=step_name,
            status=status,
            duration_ms=round(duration_ms, 2),
            summary=summary,
            details=details or {},
        )
        async with self._lock:
            q = self._channels.get(session_id)
            if q:
                await q.put(event)

    async def emit_token(self, session_id: str, token: str) -> None:
        """Stream LLM text delta token."""
        async with self._lock:
            q = self._channels.get(session_id)
            if q:
                await q.put({"event": "token", "data": token})

    async def emit_complete(self, session_id: str, result_payload: Dict[str, Any]) -> None:
        async with self._lock:
            q = self._channels.get(session_id)
            if q:
                await q.put({"event": "complete", "data": result_payload})
                # Sentinel to signal end of stream
                await q.put(None)

    async def emit_error(self, session_id: str, error_msg: str) -> None:
        async with self._lock:
            q = self._channels.get(session_id)
            if q:
                await q.put({"event": "error", "data": {"error": error_msg}})
                await q.put(None)

    async def stream_events(self, session_id: str) -> AsyncGenerator[str, None]:
        q = await self.create_channel(session_id)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, StepEvent):
                    yield item.to_sse()
                elif isinstance(item, dict):
                    evt_type = item.get("event", "message")
                    data_str = json.dumps(item.get("data", {}))
                    yield f"event: {evt_type}\ndata: {data_str}\n\n"
        finally:
            await self.remove_channel(session_id)


# Global singleton event bus
event_bus = PipelineEventBus()
