import duckdb
import logging
import time
from typing import Any, Dict, List, Tuple, Optional
import pandas as pd
from app.data.adapter import adapter

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.con = duckdb.connect(database=":memory:")
        self.initialized = False

    def init_db(self, force_refresh: bool = False):
        deals_df, wo_df = adapter.load_data(force_refresh=force_refresh)

        # Register views
        self.con.register("deals_raw", deals_df)
        self.con.register("wo_raw", wo_df)

        self.con.execute("""
            CREATE OR REPLACE VIEW deals AS
            SELECT * FROM deals_raw;
        """)

        self.con.execute("""
            CREATE OR REPLACE VIEW work_orders AS
            SELECT * FROM wo_raw;
        """)

        self.con.execute("""
            CREATE OR REPLACE VIEW deal_wo_lifecycle AS
            SELECT
                d.deal_name AS deal_name,
                d.owner_code AS deal_owner,
                d.client_code AS deal_client,
                d.deal_status,
                d.deal_stage,
                d.deal_value,
                d.weighted_deal_value,
                d.sector AS deal_sector,
                d.closure_probability,
                w.serial_no AS wo_serial,
                w.execution_status,
                w.billing_status,
                w.amount_excl_gst AS wo_contracted_excl_gst,
                w.billed_excl_gst AS wo_billed_excl_gst,
                w.collected_incl_gst AS wo_collected_incl_gst,
                w.to_be_billed_excl_gst AS wo_unbilled_excl_gst,
                w.receivable_amount AS wo_receivable,
                CASE WHEN w.deal_name IS NOT NULL THEN 1 ELSE 0 END AS has_work_order
            FROM deals d
            LEFT JOIN work_orders w ON d.join_key = w.join_key;
        """)

        self.initialized = True
        logger.info("DuckDB in-memory analytical views successfully registered.")

    def query(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[List[Dict[str, Any]], float, int]:
        """
        Executes parameterized SQL and returns (rows as dicts, execution_time_ms, row_count).
        """
        if not self.initialized:
            self.init_db()

        start_time = time.time()
        if params:
            result = self.con.execute(sql, params).fetchdf()
        else:
            result = self.con.execute(sql).fetchdf()
        duration_ms = round((time.time() - start_time) * 1000, 2)
        row_count = len(result)

        # Convert Timestamps to ISO strings for JSON serialization
        records = result.to_dict(orient="records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, pd.Timestamp):
                    r[k] = v.isoformat()
                elif pd.isna(v):
                    r[k] = None

        return records, duration_ms, row_count

db = Database()
