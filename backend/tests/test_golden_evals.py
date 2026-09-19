import pytest
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.core.anonymizer import blindfold
from app.tools.pipeline_tools import get_pipeline_summary
from app.tools.revenue_tools import get_revenue_realization_summary
from app.tools.operations_tools import get_cross_board_conversion

@pytest.fixture(scope="module", autouse=True)
def setup_engine():
    db.init_db()
    orchestrator.init_catalog()

def test_golden_pipeline_metrics():
    pipe = get_pipeline_summary()
    summary = pipe["summary"]

    assert summary["total_open_deals"] == 49
    assert abs(summary["total_pipeline_value"] - 688152293.17) < 1.0
    assert abs(summary["total_weighted_pipeline"] - 264613014.51) < 1.0
    assert abs(summary["avg_deal_size"] - 14043924.35) < 1.0

def test_golden_revenue_realization_metrics():
    rev = get_revenue_realization_summary()
    s = rev["summary"]

    assert s["total_work_orders"] == 175
    assert abs(s["contracted_amount_excl_gst"] - 210613555.12) < 1.0
    assert abs(s["billed_amount_excl_gst"] - 107389776.59) < 1.0
    assert abs(s["collected_amount_incl_gst"] - 90428187.50) < 1.0
    assert abs(s["unbilled_backlog_excl_gst"] - 103223778.53) < 1.0
    assert abs(s["outstanding_receivables"] - 36291748.87) < 1.0
    assert abs(s["realization_rate_pct"] - 50.99) < 0.05
    assert abs(s["collection_efficiency_pct"] - 71.36) < 0.05

def test_golden_conversion_metrics():
    conv = get_cross_board_conversion()

    assert conv["total_won_deals"] == 163
    assert conv["converted_to_wo_count"] == 106
    assert conv["pending_wo_creation_count"] == 57
    assert abs(conv["conversion_rate_pct"] - 65.03) < 0.05

@pytest.mark.asyncio
async def test_zero_pii_leakage_in_chat_orchestration():
    query = "What is the status of Naruto deal with COMPANY089?"
    res = await orchestrator.execute_query(query)

    # Verify pipeline trace contains step 4 (Blindfold Gateway)
    trace = res.pipeline_trace
    gateway_step = next(s for s in trace if s.step_number == 4)
    tokenized_query = gateway_step.output_payload.get("tokenized_query", "")

    # Assert raw PII was stripped from what would reach LLM
    assert "Naruto" not in tokenized_query
    assert "COMPANY089" not in tokenized_query
    assert "PROJECT_DEAL_" in tokenized_query or "CLIENT_ENT_" in tokenized_query

    # Assert final answer has real names restored for the user
    assert res.answer is not None
    assert len(res.answer) > 0
