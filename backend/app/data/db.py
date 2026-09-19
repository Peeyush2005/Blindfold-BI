"""
Database wrapper for backward compatibility.
Delegates directly to analytical DuckDBStore.
"""

from typing import Any, Dict, List, Tuple, Optional
from app.data.duckdb_store import duckdb_store


class Database:
    def __init__(self):
        self.store = duckdb_store

    def init_db(self, force_refresh: bool = False):
        self.store.initialize(force_refresh=force_refresh)

    def query(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[List[Dict[str, Any]], float, int]:
        return self.store.query(sql, params)


db = Database()
