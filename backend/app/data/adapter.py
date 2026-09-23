"""
Data adapter for Blindfold BI.

Reads the Deals and Work Orders boards from monday.com (read-only GraphQL), maps monday
columns to the canonical headers by *title*, normalizes the rows, and loads them into DuckDB.

Rules this module enforces:
  * Live monday.com data is the only production source. Local Excel fixtures are used only when
    settings.fixtures_allowed is true (development/tests) AND the files exist.
  * Nothing is reported as "monday.com" unless the rows really came from monday.com.
  * Every number in get_status()/last_stats comes from the actual fetch, never from constants.
  * If a refresh fails, the last good snapshot keeps being served and is marked stale.
"""

import asyncio
import datetime
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.config import settings
from app.data import monday_client as monday_module
from app.data.dq_ledger import dq_ledger
from app.data.duckdb_store import duckdb_store
from app.data.monday_client import MondayAPIError
from app.data.normalize import normalize_deals, normalize_work_orders

logger = logging.getLogger(__name__)

DEALS_NAME_HEADER = "Deal Name"
WO_NAME_HEADER = "Deal name masked"

DEALS_HEADERS: List[str] = [
    "Deal Name", "Owner code", "Client Code", "Deal Status", "Close Date (A)", "Closure Probability",
    "Masked Deal value", "Tentative Close Date", "Deal Stage", "Product deal", "Sector/service", "Created Date",
]
DEALS_REQUIRED: List[str] = [
    "Deal Status", "Masked Deal value", "Sector/service", "Deal Stage", "Tentative Close Date", "Created Date",
]
DEALS_NUMERIC: List[str] = ["Masked Deal value"]

WO_HEADERS: List[str] = [
    "Deal name masked", "Customer Name Code", "Serial #", "Nature of Work",
    "Last executed month of recurring project", "Execution Status", "Data Delivery Date", "Date of PO/LOI",
    "Document Type", "Probable Start Date", "Probable End Date", "BD/KAM Personnel code", "Sector", "Type of Work",
    "Is any Skylark software platform part of the client deliverables in this deal?", "Last invoice date",
    "latest invoice no.", "Amount in Rupees (Excl of GST) (Masked)", "Amount in Rupees (Incl of GST) (Masked)",
    "Billed Value in Rupees (Excl of GST.) (Masked)", "Billed Value in Rupees (Incl of GST.) (Masked)",
    "Collected Amount in Rupees (Incl of GST.) (Masked)", "Amount to be billed in Rs. (Exl. of GST) (Masked)",
    "Amount to be billed in Rs. (Incl. of GST) (Masked)", "Amount Receivable (Masked)", "AR Priority account",
    "Quantity by Ops", "Quantities as per PO", "Quantity billed (till date)", "Balance in quantity",
    "Invoice Status", "Expected Billing Month", "Actual Billing Month", "Actual Collection Month",
    "WO Status (billed)", "Collection status", "Collection Date", "Billing Status",
]
WO_REQUIRED: List[str] = [
    "Sector", "Execution Status", "Amount in Rupees (Excl of GST) (Masked)",
    "Billed Value in Rupees (Excl of GST.) (Masked)", "Collected Amount in Rupees (Incl of GST.) (Masked)",
    "Amount Receivable (Masked)",
]
WO_NUMERIC: List[str] = [
    "Amount in Rupees (Excl of GST) (Masked)", "Amount in Rupees (Incl of GST) (Masked)",
    "Billed Value in Rupees (Excl of GST.) (Masked)", "Billed Value in Rupees (Incl of GST.) (Masked)",
    "Collected Amount in Rupees (Incl of GST.) (Masked)", "Amount to be billed in Rs. (Exl. of GST) (Masked)",
    "Amount to be billed in Rs. (Incl. of GST) (Masked)", "Amount Receivable (Masked)",
    "Quantity by Ops", "Quantity billed (till date)", "Balance in quantity",
]


class DataUnavailableError(RuntimeError):
    """No usable data: monday.com is not connected (or failed) and no snapshot exists."""


def _canon(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _clean(value: Any) -> Any:
    """monday returns "" or null for empty cells; treat both as missing, like an empty Excel cell."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v != "" else None
    return value


def _cell_value(cv: Dict[str, Any]) -> Any:
    """Prefer the exact stored value for number columns (the display text can carry formatting)."""
    col_type = (cv.get("type") or "").lower()
    if col_type in ("numbers", "numeric"):
        raw = cv.get("value")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, (str, int, float)):
                    return _clean(str(parsed))
            except (ValueError, TypeError):
                pass
        text = _clean(cv.get("text"))
        if isinstance(text, str):
            text = re.sub(r"[^0-9.\-]", "", text) or None
        return text
    return _clean(cv.get("text"))


def board_to_frame(
    board: Dict[str, Any],
    name_header: str,
    expected_headers: List[str],
    required_headers: List[str],
    numeric_headers: List[str],
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Convert a monday board (columns + items) into a DataFrame using the canonical source headers."""
    canon_to_header = {_canon(h): h for h in expected_headers}
    id_to_header: Dict[str, str] = {}
    unmatched: List[str] = []
    present: set = {name_header}
    for col in board.get("columns", []):
        if col.get("id") == "name":
            continue
        title = col.get("title", "")
        header = canon_to_header.get(_canon(title))
        if header:
            id_to_header[col["id"]] = header
            present.add(header)
        else:
            unmatched.append(title)

    missing_required = [h for h in required_headers if h not in present]
    if missing_required:
        raise DataUnavailableError(
            f"Board '{board.get('name')}' is missing required columns: {', '.join(missing_required)}. "
            "Check the column titles match the imported sheet headers."
        )

    rows: List[Dict[str, Any]] = []
    for item in board.get("items", []):
        row: Dict[str, Any] = {name_header: _clean(item.get("name"))}
        for cv in item.get("column_values", []):
            header = id_to_header.get(cv.get("id"))
            if header:
                row[header] = _cell_value(cv)
        rows.append(row)

    df = pd.DataFrame(rows)
    for header in expected_headers:
        if header not in df.columns:
            df[header] = None
    df = df[expected_headers]
    for header in numeric_headers:
        df[header] = pd.to_numeric(df[header], errors="coerce")

    info = {
        "board_id": str(board.get("id")),
        "board_name": board.get("name"),
        "items_fetched": len(rows),
        "pages": board.get("pages"),
        "api_calls": board.get("api_calls"),
        "fetch_ms": board.get("duration_ms"),
        "columns_matched": len(present) - 1,
        "columns_unmatched": unmatched,
    }
    return df, info


class DataAdapter:
    def __init__(self, client: Optional[monday_module.MondayClient] = None):
        self._client = client
        self.deals_df: Optional[pd.DataFrame] = None
        self.wo_df: Optional[pd.DataFrame] = None
        self.last_synced: Optional[datetime.datetime] = None
        self._synced_monotonic: Optional[float] = None
        self.source: str = "none"  # "monday.com" | "fixture" | "none"
        self.is_stale: bool = False
        self.last_error: Optional[str] = None
        self.last_stats: Dict[str, Any] = {}
        self._lock: Optional[asyncio.Lock] = None

    # ------------------------------------------------------------------ helpers
    @property
    def client(self) -> monday_module.MondayClient:
        return self._client or monday_module.monday_client

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def has_data(self) -> bool:
        return self.deals_df is not None and self.wo_df is not None

    def _board_ids(self) -> Tuple[str, str]:
        deals = (self.client.deals_board_id if self.client and self.client.deals_board_id else settings.MONDAY_DEALS_BOARD_ID) or ""
        wo = (self.client.wo_board_id if self.client and self.client.wo_board_id else settings.MONDAY_WO_BOARD_ID) or ""
        return (str(deals).strip(), str(wo).strip())

    @property
    def monday_configured(self) -> bool:
        deals_id, wo_id = self._board_ids()
        token = ((self.client.api_token if self.client and self.client.api_token else settings.MONDAY_API_TOKEN) or "").strip()
        # An injected client (tests) may use a transport instead of a token.
        has_credentials = bool(token) or (self._client is not None and self._client.transport is not None)
        return bool(has_credentials and deals_id and wo_id)

    def _is_fresh(self) -> bool:
        return (
            self.has_data
            and not self.is_stale
            and self._synced_monotonic is not None
            and (time.monotonic() - self._synced_monotonic) < settings.CACHE_TTL_SECONDS
        )

    def _install(self, d_df: pd.DataFrame, w_df: pd.DataFrame, source: str, stats: Dict[str, Any]) -> None:
        self.deals_df, self.wo_df = d_df, w_df
        self.source = source
        self.is_stale = False
        self.last_error = None
        self.last_synced = datetime.datetime.now()
        self._synced_monotonic = time.monotonic()
        self.last_stats = stats
        duckdb_store.initialize(deals_df=d_df, wo_df=w_df, force_refresh=True)
        from app.core.gateway import blindfold_gateway  # local import: avoid a circular import at module load
        blindfold_gateway.init_catalog()

    # ------------------------------------------------------------------ live path
    async def _fetch_live(self) -> Dict[str, Any]:
        deals_id, wo_id = self._board_ids()
        t0 = time.time()
        deals_board, wo_board = await asyncio.gather(
            self.client.fetch_board(deals_id), self.client.fetch_board(wo_id)
        )
        raw_deals, deals_info = board_to_frame(deals_board, DEALS_NAME_HEADER, DEALS_HEADERS, DEALS_REQUIRED, DEALS_NUMERIC)
        raw_wo, wo_info = board_to_frame(wo_board, WO_NAME_HEADER, WO_HEADERS, WO_REQUIRED, WO_NUMERIC)

        dq_ledger.clear()
        d_df = normalize_deals(raw_deals)
        w_df = normalize_work_orders(raw_wo)

        return {
            "d_df": d_df,
            "w_df": w_df,
            "stats": self._build_stats(
                "monday.com", len(raw_deals), len(d_df), len(raw_wo), len(w_df),
                fetch_ms=round((time.time() - t0) * 1000, 1),
                boards={"deals": deals_info, "work_orders": wo_info},
            ),
        }

    def _build_stats(
        self, source: str, deals_raw: int, deals_clean: int, wo_raw: int, wo_clean: int,
        fetch_ms: float, boards: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "source": source,
            "fetched_at": datetime.datetime.now().isoformat(),
            "fetch_ms": fetch_ms,
            "boards": boards or {},
            "rows": {
                "deals_raw": deals_raw, "deals_clean": deals_clean, "deals_removed": deals_raw - deals_clean,
                "work_orders_raw": wo_raw, "work_orders_clean": wo_clean, "work_orders_removed": wo_raw - wo_clean,
            },
            "dq": [
                {"code": a.code, "name": a.rule_name, "affected_count": a.affected_count}
                for a in dq_ledger.get_all()
            ],
            "monday_calls_today": getattr(self.client, "calls_today", None),
        }

    # ------------------------------------------------------------------ fixture path (dev/tests only)
    def _load_fixtures(self) -> bool:
        if not settings.fixtures_allowed:
            return False
        if not (settings.DEALS_EXCEL_PATH.exists() and settings.WO_EXCEL_PATH.exists()):
            return False
        t0 = time.time()
        raw_d = pd.read_excel(settings.DEALS_EXCEL_PATH, sheet_name=0)
        dq_ledger.clear()
        d_df = normalize_deals(settings.DEALS_EXCEL_PATH)
        w_df = normalize_work_orders(settings.WO_EXCEL_PATH)
        stats = self._build_stats(
            "fixture", len(raw_d), len(d_df), len(w_df), len(w_df), fetch_ms=round((time.time() - t0) * 1000, 1)
        )
        self._install(d_df, w_df, "fixture", stats)
        return True

    def load_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Synchronous loader kept for scripts/tests: local fixtures only, and only where allowed."""
        if self.has_data and not force_refresh:
            return self.deals_df, self.wo_df  # type: ignore[return-value]
        if not self._load_fixtures():
            raise DataUnavailableError(
                "No data available: monday.com is not connected and local fixtures are not allowed here."
            )
        return self.deals_df, self.wo_df  # type: ignore[return-value]

    # ------------------------------------------------------------------ public async API
    async def refresh(self, force: bool = False) -> Dict[str, Any]:
        """Refresh from monday.com. Single-flight. Never raises; inspect get_status() for the outcome."""
        async with self._get_lock():
            if not force and self._is_fresh():
                return self.get_status()

            if self.monday_configured:
                try:
                    result = await self._fetch_live()
                    self._install(result["d_df"], result["w_df"], "monday.com", result["stats"])
                    logger.info(
                        "Loaded live monday.com data: %s deals, %s work orders",
                        len(result["d_df"]), len(result["w_df"]),
                    )
                    return self.get_status()
                except (MondayAPIError, DataUnavailableError) as exc:
                    self.last_error = str(exc)
                except Exception as exc:  # network, budget, parsing
                    self.last_error = f"{type(exc).__name__}: {exc}"
                logger.error("monday.com refresh failed: %s", self.last_error)
            else:
                self.last_error = "monday.com is not configured (missing token or board IDs)."

            if self.has_data and self.source == "monday.com":
                self.is_stale = True  # keep serving the last good live snapshot, clearly labelled
            elif not self.has_data:
                self._load_fixtures()  # dev/tests only; the source is then labelled "fixture"
            return self.get_status()

    async def ensure_fresh(self) -> Dict[str, Any]:
        """Called per request: refreshes when the snapshot is older than the TTL or missing."""
        if self._is_fresh():
            return self.get_status()
        return await self.refresh()

    def get_status(self) -> Dict[str, Any]:
        rows = (self.last_stats or {}).get("rows", {})
        age = None
        if self._synced_monotonic is not None:
            age = round(time.monotonic() - self._synced_monotonic)
        if not self.has_data:
            state = "unavailable"
        elif self.is_stale:
            state = "stale_snapshot"
        else:
            state = self.source
        return {
            "source": state,
            "connected": self.has_data and self.source == "monday.com" and not self.is_stale,
            "has_data": self.has_data,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
            "snapshot_age_seconds": age,
            "is_stale": self.is_stale,
            "error": self.last_error,
            "deals_count": rows.get("deals_clean", len(self.deals_df) if self.deals_df is not None else 0),
            "work_orders_count": rows.get("work_orders_clean", len(self.wo_df) if self.wo_df is not None else 0),
            "stats": self.last_stats,
        }


adapter = DataAdapter()