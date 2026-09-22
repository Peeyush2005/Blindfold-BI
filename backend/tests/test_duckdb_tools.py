import pytest
from app.data.db import db
from app.tools.pipeline_tools import get_pipeline_summary
from app.tools.revenue_tools import get_revenue_realization_summary
from app.tools.operations_tools import get_cross_board_conversion, get_work_order_health, get_data_debt_report
from app.tools.executive_tools import get_executive_brief

@pytest.fixture(scope="module", autouse=True)
def init_database():
    db.init_db()

def test_pipeline_summary():
    result = get_pipeline_summary()
    assert "summary" in result
    assert "audit" in result
    assert result["summary"]["total_open_deals"] == 49
    assert result["summary"]["total_pipeline_value"] > 0
    assert result["audit"]["rows_scanned"] == 342

def test_pipeline_summary_filtered():
    result = get_pipeline_summary(sector="Mining")
    assert result["summary"]["total_open_deals"] == 9
    assert result["summary"]["total_pipeline_value"] == 29083888.2

def test_revenue_realization_summary():
    result = get_revenue_realization_summary()
    assert "summary" in result
    s = result["summary"]
    assert s["total_work_orders"] in (175, 176)
    assert abs(s["contracted_amount_excl_gst"] - 211649409.21) < 1.0 or abs(s["contracted_amount_excl_gst"] - 210613555.12) < 1.0
    assert abs(s["billed_amount_excl_gst"] - 107389776.59) < 1.0
    assert abs(s["realization_rate_pct"] - 50.74) < 0.5 or abs(s["realization_rate_pct"] - 50.99) < 0.5
    assert s["collection_efficiency_pct"] == 71.36

def test_cross_board_conversion():
    result = get_cross_board_conversion()
    assert result["total_won_deals"] == 163
    assert result["converted_to_wo_count"] == 106
    assert result["conversion_rate_pct"] == 65.03

def test_work_order_health():
    result = get_work_order_health()
    assert "execution_breakdown" in result
    assert "billing_status_breakdown" in result
    assert result["total_orders"] in (175, 176)
    assert result["delayed_orders_count"] > 0

def test_data_debt_report():
    result = get_data_debt_report()
    assert result["total_debt_records"] == 31
    assert result["high_severity_count"] == 29
    assert len(result["records"]) == 31

def test_executive_brief():
    result = get_executive_brief()
    assert "kpis" in result
    assert "wins" in result
    assert "risks" in result
    assert "recommendations" in result
    assert "deltas" in result  # kept for backwards compatibility; empty until snapshot history is stored
    assert len(result["wins"]) >= 1
    assert len(result["risks"]) >= 1
    # every win/risk/recommendation must be derived text, never one of the old fixed strings
    frozen_strings = [
        "Contracted order book of ₹21.16 Cr demonstrates robust core market demand",
        "₹3.63 Cr in outstanding net receivables requires active collection follow-up",
        "Trigger immediate billing on 17 completed-unbilled work orders to recover ₹1.46 Cr",
    ]
    for s in result["wins"] + result["risks"] + result["recommendations"]:
        assert s not in frozen_strings
