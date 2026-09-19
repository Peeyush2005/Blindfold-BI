"""
Ground Truth Oracle for Blindfold BI.
Evaluates metrics directly using pure pandas transformations to provide an independent
verification standard against DuckDB queries and analytical tools (Section 3.6).
"""

from typing import Dict, Any, Optional
import pandas as pd
from pathlib import Path

from app.config import settings
from app.data.normalize import normalize_deals, normalize_work_orders, ENERGY_SECTORS


class GroundTruthOracle:
    def __init__(self, deals_path: Optional[Path] = None, wo_path: Optional[Path] = None):
        self.deals_path = deals_path or settings.DEALS_EXCEL_PATH
        self.wo_path = wo_path or settings.WO_EXCEL_PATH
        self.deals_df = normalize_deals(self.deals_path)
        self.wo_df = normalize_work_orders(self.wo_path)

    def get_ground_truth_metrics(self) -> Dict[str, Any]:
        """
        Computes the canonical 16 Section 3.6 ground truth metrics.
        """
        d = self.deals_df
        w = self.wo_df

        # Deals metrics
        total_deals = len(d)
        open_mask = d["status"] == "Open"
        open_deals = d[open_mask]
        open_deals_count = len(open_deals)
        open_deals_with_value = open_deals[open_deals["deal_value"] > 0]
        open_deals_with_value_count = len(open_deals_with_value)
        open_pipeline_value = float(open_deals["deal_value"].sum())

        won_mask = d["status"] == "Won"
        won_deals = d[won_mask]
        won_deals_count = len(won_deals)
        won_deals_with_value = won_deals[won_deals["deal_value"] > 0]
        won_deals_with_value_count = len(won_deals_with_value)
        won_deal_value = float(won_deals["deal_value"].sum())

        tender_open = open_deals[open_deals["sector"] == "Tender"]
        tender_open_val = float(tender_open["deal_value"].sum())
        tender_open_pct = (tender_open_val / open_pipeline_value * 100) if open_pipeline_value > 0 else 0.0

        non_tender_open = open_deals[open_deals["sector"] != "Tender"]
        non_tender_open_val = float(non_tender_open["deal_value"].sum())

        energy_open = open_deals[open_deals["sector"].isin(ENERGY_SECTORS)]
        energy_open_count = len(energy_open)
        energy_open_val = float(energy_open["deal_value"].sum())

        # Work Orders metrics
        total_wo = len(w)
        wo_contracted_excl_gst = float(w["amount_excl_gst"].sum())
        wo_receivable_net = float(w["receivable_amount"].sum())
        wo_negative_receivable_count = int((w["receivable_amount"] < 0).sum())

        return {
            "total_deals": total_deals,
            "open_deals_count": open_deals_count,
            "open_deals_with_value_count": open_deals_with_value_count,
            "open_pipeline_value": open_pipeline_value,
            "won_deals_count": won_deals_count,
            "won_deals_with_value_count": won_deals_with_value_count,
            "won_deal_value": won_deal_value,
            "tender_open_val": tender_open_val,
            "tender_open_pct": tender_open_pct,
            "non_tender_open_val": non_tender_open_val,
            "energy_open_count": energy_open_count,
            "energy_open_val": energy_open_val,
            "total_work_orders": total_wo,
            "wo_contracted_excl_gst": wo_contracted_excl_gst,
            "wo_receivable_net": wo_receivable_net,
            "wo_negative_receivable_count": wo_negative_receivable_count,
        }


oracle = GroundTruthOracle()
