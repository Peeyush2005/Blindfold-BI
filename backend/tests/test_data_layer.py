"""
Test suite for Phase 1 Data Layer:
- Read-only MondayClient and MutationForbiddenError
- FakeMondayTransport offline mock
- DQLedger anomaly registry
- Normalization pipelines (Deals 332 rows, Work Orders 176 rows)
- DuckDBStore analytical engine and analytical views
- GroundTruthOracle alignment with Section 3.6
"""

import pytest
import pandas as pd
from app.data.monday_client import MondayClient, MutationForbiddenError, CallBudgetExceededError, FakeMondayTransport
from app.data.dq_ledger import dq_ledger
from app.data.duckdb_store import duckdb_store
from app.data.snapshot import snapshot_service
from tests.evals.oracle import GroundTruthOracle


@pytest.mark.asyncio
async def test_monday_client_read_only_and_transport():
    transport = FakeMondayTransport()
    client = MondayClient(api_token="test-token", transport=transport, daily_budget=5)

    # 1. Valid read query
    res = await client.query("query { boards { id name } }")
    assert "boards" in res
    assert len(res["boards"]) == 2
    assert client.calls_today == 1

    # 2. Mutation attempt raises MutationForbiddenError
    with pytest.raises(MutationForbiddenError):
        await client.query("mutation { create_item (board_id: 123, item_name: 'test') { id } }")

    with pytest.raises(MutationForbiddenError):
        await client.query("MUTATION { change_simple_column_value { id } }")


@pytest.mark.asyncio
async def test_monday_client_budget_ceiling():
    transport = FakeMondayTransport()
    client = MondayClient(api_token="test-token", transport=transport, daily_budget=2)

    await client.query("query { me { id } }")
    await client.query("query { me { id } }")
    assert client.calls_today == 2

    with pytest.raises(CallBudgetExceededError):
        await client.query("query { me { id } }")


def test_dq_ledger_recording_and_export():
    anomalies = dq_ledger.get_all()
    assert len(anomalies) > 0

    codes = [a.code for a in anomalies]
    # Check that representative DQ codes exist
    assert "DQ001" in codes
    assert "DQ002" in codes
    assert "DQ008" in codes
    assert "DQ009" in codes

    # Test export to dataframe
    df = dq_ledger.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(anomalies)
    assert "DQ Code" in df.columns
    assert "Severity" in df.columns


def test_normalization_and_oracle_section_3_6():
    oracle = GroundTruthOracle()
    metrics = oracle.get_ground_truth_metrics()

    # Ground truth spot checks (Section 3.6)
    assert metrics["total_deals"] == 332
    assert metrics["open_deals_count"] == 49
    assert metrics["open_deals_with_value_count"] == 47
    assert round(metrics["open_pipeline_value"] / 1e7, 2) == 68.82
    assert metrics["won_deals_count"] == 153
    assert metrics["won_deals_with_value_count"] == 64
    assert round(metrics["won_deal_value"] / 1e7, 2) == 9.50
    assert round(metrics["tender_open_val"] / 1e7, 2) == 53.20
    assert round(metrics["tender_open_pct"], 1) == 77.3
    assert round(metrics["non_tender_open_val"] / 1e7, 2) == 15.62
    assert metrics["energy_open_count"] == 12
    assert round(metrics["energy_open_val"] / 1e7, 2) == 3.19

    assert metrics["total_work_orders"] == 176
    assert round(metrics["wo_contracted_excl_gst"] / 1e7, 2) == 21.16
    assert round(metrics["wo_receivable_net"] / 1e7, 2) == 3.63
    assert metrics["wo_negative_receivable_count"] == 11


def test_duckdb_store_analytical_views():
    duckdb_store.initialize(force_refresh=True)

    # Check deals view
    records, duration_ms, count = duckdb_store.query("SELECT COUNT(*) AS c, SUM(deal_value) AS v FROM deals WHERE status = 'Open'")
    assert count == 1
    assert records[0]["c"] == 49
    assert round(records[0]["v"] / 1e7, 2) == 68.82
    assert duration_ms < 50.0  # sub-50ms test threshold

    # Check work orders view
    records, duration_ms, count = duckdb_store.query("SELECT COUNT(*) AS c, SUM(amount_excl_gst) AS amt FROM work_orders")
    assert records[0]["c"] == 176
    assert round(records[0]["amt"] / 1e7, 2) == 21.16

    # Check sector reconciliation view
    records, duration_ms, count = duckdb_store.query("SELECT * FROM sector_reconciliation WHERE sector = 'Tender'")
    assert count == 1
    assert records[0]["open_deals_count"] > 0
    assert round(records[0]["open_pipeline_value"] / 1e7, 2) == 53.20


def test_snapshot_service():
    deals_df, wo_df = snapshot_service.load_snapshot(force_refresh=True)
    assert len(deals_df) == 332
    assert len(wo_df) == 176
    meta = snapshot_service.get_metadata()
    assert meta["deals_count"] == 332
    assert meta["work_orders_count"] == 176
    assert len(meta["checksum"]) == 16
    assert not meta["is_stale"]
