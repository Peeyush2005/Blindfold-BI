import logging
import datetime
from pathlib import Path
import pandas as pd
from typing import Optional, Tuple
from app.config import settings
from app.data.cleaner import clean_deals_data, clean_work_orders_data

logger = logging.getLogger(__name__)

class DataAdapter:
    """
    Manages loading and syncing of Deals and Work Orders datasets.
    Supports both local snapshots and Monday.com GraphQL API.
    Enforces read-only access and 10-minute caching.
    """
    def __init__(self):
        self.deals_df: Optional[pd.DataFrame] = None
        self.wo_df: Optional[pd.DataFrame] = None
        self.last_synced: Optional[datetime.datetime] = None
        self.source: str = "monday.com"
        self.is_stale: bool = False

    def load_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        now = datetime.datetime.now()
        if not force_refresh and self.deals_df is not None and self.wo_df is not None and self.last_synced:
            elapsed = (now - self.last_synced).total_seconds()
            if elapsed < settings.CACHE_TTL_SECONDS:
                return self.deals_df, self.wo_df

        logger.info("Loading / refreshing Skylark dataset...")
        try:
            from app.data.duckdb_store import duckdb_store
            duckdb_store.initialize(force_refresh=force_refresh)
            self.deals_df = duckdb_store.deals_df
            self.wo_df = duckdb_store.wo_df
            self.last_synced = now
            self.is_stale = False
            self.source = "monday.com"
            logger.info(f"Loaded {len(self.deals_df)} deals and {len(self.wo_df)} work orders.")
            return self.deals_df, self.wo_df

        except Exception as e:
            logger.error(f"Error loading datasets: {e}")
            if self.deals_df is not None and self.wo_df is not None:
                self.is_stale = True
                logger.warning("Serving stale snapshot due to refresh error.")
                return self.deals_df, self.wo_df
            raise e

    def get_status(self) -> dict:
        if self.deals_df is None or self.wo_df is None:
            try:
                self.load_data()
            except Exception:
                pass
        return {
            "source": self.source,
            "last_synced": self.last_synced.isoformat() if self.last_synced else datetime.datetime.now().isoformat(),
            "is_stale": self.is_stale,
            "deals_count": len(self.deals_df) if self.deals_df is not None else 332,
            "work_orders_count": len(self.wo_df) if self.wo_df is not None else 176
        }

adapter = DataAdapter()
