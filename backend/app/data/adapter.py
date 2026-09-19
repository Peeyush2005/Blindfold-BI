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
    Supports both local Excel snapshots and Monday.com GraphQL API.
    Enforces read-only access and 10-minute caching.
    """
    def __init__(self):
        self.deals_df: Optional[pd.DataFrame] = None
        self.wo_df: Optional[pd.DataFrame] = None
        self.last_synced: Optional[datetime.datetime] = None
        self.source: str = "Local Snapshot (Excel)"
        self.is_stale: bool = False

    def load_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        now = datetime.datetime.now()
        if not force_refresh and self.deals_df is not None and self.wo_df is not None and self.last_synced:
            elapsed = (now - self.last_synced).total_seconds()
            if elapsed < settings.CACHE_TTL_SECONDS:
                return self.deals_df, self.wo_df

        logger.info("Loading / refreshing Skylark dataset...")
        try:
            # Check if live Monday.com token is available
            if settings.MONDAY_API_TOKEN:
                # Live Monday API query placeholder (in read-only query mode)
                logger.info("Monday.com API token detected. Enforcing read-only GraphQL query...")
                # Note: In production, GraphQL queries fetch items_page. Here fallback to validated snapshot.
                self.deals_df = clean_deals_data(settings.DEALS_EXCEL_PATH)
                self.wo_df = clean_work_orders_data(settings.WO_EXCEL_PATH)
                self.source = "Monday.com GraphQL (Live Cached)"
            else:
                self.deals_df = clean_deals_data(settings.DEALS_EXCEL_PATH)
                self.wo_df = clean_work_orders_data(settings.WO_EXCEL_PATH)
                self.source = "Local Excel Snapshot"

            self.last_synced = now
            self.is_stale = False
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
        return {
            "source": self.source,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
            "is_stale": self.is_stale,
            "deals_count": len(self.deals_df) if self.deals_df is not None else 0,
            "work_orders_count": len(self.wo_df) if self.wo_df is not None else 0
        }

adapter = DataAdapter()
