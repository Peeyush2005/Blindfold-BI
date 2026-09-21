"""
Snapshot management service for Blindfold BI.
Maintains data snapshots with SHA-256 checksums, metadata, and 10-minute TTL caching.
Supports snapshot diffing for leadership period-over-period briefs.
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
import duckdb

from app.config import settings
from app.data.normalize import normalize_deals, normalize_work_orders
from app.data.dq_ledger import dq_ledger

logger = logging.getLogger(__name__)

SNAPSHOT_TTL_SECONDS = 600


class SnapshotService:
    def __init__(self):
        self.deals_df: Optional[pd.DataFrame] = None
        self.wo_df: Optional[pd.DataFrame] = None
        self.last_synced: Optional[float] = None
        self.checksum: str = ""
        self.source: str = "monday.com (Snapshot)"
        self.is_stale: bool = False
        self.as_of_date: str = "15 Jan 2026"

    def _compute_checksum(self, deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> str:
        hasher = hashlib.sha256()
        hasher.update(str(len(deals_df)).encode("utf-8"))
        hasher.update(str(deals_df["deal_value"].sum()).encode("utf-8"))
        hasher.update(str(len(wo_df)).encode("utf-8"))
        hasher.update(str(wo_df["amount_excl_gst"].sum()).encode("utf-8"))
        return hasher.hexdigest()[:16]

    def load_snapshot(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        now = time.time()
        if not force_refresh and self.deals_df is not None and self.wo_df is not None and self.last_synced:
            if (now - self.last_synced) < SNAPSHOT_TTL_SECONDS:
                return self.deals_df, self.wo_df

        logger.info("Refreshing Blindfold BI data snapshot...")
        try:
            if settings.DEALS_EXCEL_PATH.exists() and settings.WO_EXCEL_PATH.exists():
                d_df = normalize_deals(settings.DEALS_EXCEL_PATH)
                w_df = normalize_work_orders(settings.WO_EXCEL_PATH)
            else:
                raise FileNotFoundError(f"Fixture datasets not found at {settings.DEALS_EXCEL_PATH} or {settings.WO_EXCEL_PATH}")

            self.deals_df = d_df
            self.wo_df = w_df
            self.last_synced = now
            self.checksum = self._compute_checksum(d_df, w_df)
            self.is_stale = False

            logger.info(f"Snapshot refreshed: {len(d_df)} deals, {len(w_df)} work orders, hash: {self.checksum}")
            return self.deals_df, self.wo_df
        except Exception as e:
            logger.error(f"Error loading snapshot: {e}")
            if self.deals_df is not None and self.wo_df is not None:
                self.is_stale = True
                return self.deals_df, self.wo_df
            raise e

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "connected": bool(settings.MONDAY_API_TOKEN) or (self.deals_df is not None and len(self.deals_df) > 0),
            "last_synced_timestamp": self.last_synced,
            "as_of": self.as_of_date,
            "checksum": self.checksum,
            "is_stale": self.is_stale,
            "ttl_seconds": SNAPSHOT_TTL_SECONDS,
            "deals_count": len(self.deals_df) if self.deals_df is not None else 0,
            "work_orders_count": len(self.wo_df) if self.wo_df is not None else 0,
            "dq_anomalies_count": len(dq_ledger.get_all()),
        }


snapshot_service = SnapshotService()
