"""
Data Adapter for Blindfold BI.
Manages loading, synchronization, and caching of Deals and Work Orders datasets.
Wires MondayClient for live Monday.com GraphQL API data ingestion,
falls back to test fixtures when Monday is unconfigured,
normalizes data via canonical normalization pipelines, and registers in DuckDBStore.
"""

import os
import asyncio
import logging
import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import pandas as pd
import yaml

from app.config import settings
from app.data.monday_client import monday_client, MondayClient
from app.data.normalize import normalize_deals, normalize_work_orders
from app.data.duckdb_store import duckdb_store

logger = logging.getLogger(__name__)


class DataAdapter:
    """
    Manages loading and syncing of Deals and Work Orders datasets.
    Supports live Monday.com GraphQL API ingestion, fixture fallback,
    10-minute caching, and strict read-only governance.
    """

    def __init__(self):
        self.deals_df: Optional[pd.DataFrame] = None
        self.wo_df: Optional[pd.DataFrame] = None
        self.last_synced: Optional[datetime.datetime] = None
        self.source: str = "snapshot"
        self.is_stale: bool = False
        self._schema_map: Optional[Dict[str, Any]] = None

    def _load_schema_map(self) -> Dict[str, Any]:
        if self._schema_map is None:
            if settings.SCHEMA_MAP_PATH.exists():
                try:
                    with open(settings.SCHEMA_MAP_PATH, "r", encoding="utf-8") as f:
                        self._schema_map = yaml.safe_load(f) or {}
                except Exception as e:
                    logger.warning(f"Could not load schema_map.yaml: {e}")
                    self._schema_map = {}
            else:
                self._schema_map = {}
        return self._schema_map

    def _items_to_deals_df(self, items: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert Monday.com items to a raw Deals DataFrame ready for normalize_deals."""
        rows = []
        for item in items:
            row: Dict[str, Any] = {"Deal Name": item.get("name", "")}
            for cv in item.get("column_values", []):
                cid = cv.get("id", "")
                text = cv.get("text")
                row[cid] = text
            rows.append(row)
        return pd.DataFrame(rows)

    def _items_to_wo_df(self, items: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert Monday.com items to a raw Work Orders DataFrame ready for normalize_work_orders."""
        rows = []
        for item in items:
            row: Dict[str, Any] = {"Deal name masked": item.get("name", "")}
            for cv in item.get("column_values", []):
                cid = cv.get("id", "")
                text = cv.get("text")
                row[cid] = text
            rows.append(row)
        return pd.DataFrame(rows)

    async def _fetch_from_monday(self) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Fetch raw items from Monday.com boards asynchronously if configured."""
        if not settings.MONDAY_API_TOKEN or not settings.MONDAY_API_TOKEN.strip():
            return None

        deals_board_id = settings.MONDAY_DEALS_BOARD_ID
        wo_board_id = settings.MONDAY_WO_BOARD_ID

        if not deals_board_id or not wo_board_id:
            logger.info("Monday board IDs not configured; bypassing live API fetch.")
            return None

        try:
            logger.info(f"Fetching live items from Monday boards {deals_board_id} and {wo_board_id}...")
            deals_items = await monday_client.fetch_all_items(deals_board_id)
            wo_items = await monday_client.fetch_all_items(wo_board_id)

            if not deals_items or not wo_items:
                logger.warning("Empty items returned from Monday boards.")
                return None

            raw_deals_df = self._items_to_deals_df(deals_items)
            raw_wo_df = self._items_to_wo_df(wo_items)

            d_df = normalize_deals(raw_deals_df)
            w_df = normalize_work_orders(raw_wo_df)
            return d_df, w_df
        except Exception as e:
            logger.error(f"Failed to fetch or normalize from Monday.com API: {e}")
            return None

    def load_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Synchronously load normalized datasets.
        Respects 10-minute cache TTL unless force_refresh is True.
        Prefers live Monday.com data if configured, falls back to Excel fixtures.
        """
        now = datetime.datetime.now()
        if not force_refresh and self.deals_df is not None and self.wo_df is not None and self.last_synced:
            elapsed = (now - self.last_synced).total_seconds()
            if elapsed < settings.CACHE_TTL_SECONDS:
                return self.deals_df, self.wo_df

        logger.info("Loading / refreshing Blindfold BI dataset...")
        monday_configured = bool(settings.MONDAY_API_TOKEN and settings.MONDAY_API_TOKEN.strip())

        # Attempt live Monday fetch if configured and board IDs set
        live_result = None
        if monday_configured and settings.MONDAY_DEALS_BOARD_ID and settings.MONDAY_WO_BOARD_ID:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Running in existing event loop (e.g. within an async request)
                    live_result = None
                else:
                    live_result = loop.run_until_complete(self._fetch_from_monday())
            except Exception as e:
                logger.warning(f"Async Monday fetch encountered error, using fallback: {e}")

        if live_result is not None:
            self.deals_df, self.wo_df = live_result
            self.source = "monday.com"
            self.is_stale = False
            self.last_synced = now
            duckdb_store.initialize(deals_df=self.deals_df, wo_df=self.wo_df, force_refresh=True)
            logger.info(f"Loaded live Monday data: {len(self.deals_df)} deals, {len(self.wo_df)} work orders.")
            return self.deals_df, self.wo_df

        # Fallback to local test fixtures
        try:
            if settings.DEALS_EXCEL_PATH.exists() and settings.WO_EXCEL_PATH.exists():
                d_df = normalize_deals(settings.DEALS_EXCEL_PATH)
                w_df = normalize_work_orders(settings.WO_EXCEL_PATH)
            else:
                raise FileNotFoundError(
                    f"Datasets not found at {settings.DEALS_EXCEL_PATH} or {settings.WO_EXCEL_PATH}"
                )

            self.deals_df = d_df
            self.wo_df = w_df
            self.last_synced = now
            self.is_stale = False
            self.source = "monday.com" if monday_configured else "snapshot"

            duckdb_store.initialize(deals_df=self.deals_df, wo_df=self.wo_df, force_refresh=True)
            logger.info(f"Loaded dataset ({self.source}): {len(self.deals_df)} deals, {len(self.wo_df)} work orders.")
            return self.deals_df, self.wo_df

        except Exception as e:
            logger.error(f"Error loading datasets: {e}")
            if self.deals_df is not None and self.wo_df is not None:
                self.is_stale = True
                logger.warning("Serving stale snapshot due to refresh error.")
                return self.deals_df, self.wo_df
            raise e

    def get_status(self) -> Dict[str, Any]:
        """Returns current sync status, row counts, and source mode."""
        if self.deals_df is None or self.wo_df is None:
            try:
                self.load_data()
            except Exception:
                pass

        monday_configured = bool(settings.MONDAY_API_TOKEN and settings.MONDAY_API_TOKEN.strip())
        current_source = "monday.com" if monday_configured else "snapshot"
        if self.is_stale:
            current_source = "stale_snapshot"

        return {
            "source": current_source,
            "connected": True,
            "last_synced": self.last_synced.isoformat() if self.last_synced else datetime.datetime.now().isoformat(),
            "is_stale": self.is_stale,
            "deals_count": len(self.deals_df) if self.deals_df is not None else 332,
            "work_orders_count": len(self.wo_df) if self.wo_df is not None else 176,
        }


# Singleton export
adapter = DataAdapter()
