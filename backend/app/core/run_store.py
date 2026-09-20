"""
In-memory store for Blindfold BI analytical runs.
Supports run history lookup, inspection, and replay via GET /api/v1/runs/{run_id}.
"""

import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from app.models.v1 import RunRecord

class RunStore:
    def __init__(self, max_size: int = 1000):
        self._runs: OrderedDict[str, RunRecord] = OrderedDict()
        self.max_size = max_size

    def save_run(self, run: RunRecord) -> None:
        if len(self._runs) >= self.max_size:
            self._runs.popitem(last=False)
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    def list_recent(self, limit: int = 20) -> List[RunRecord]:
        items = list(self._runs.values())
        return items[-limit:][::-1]


run_store = RunStore()
