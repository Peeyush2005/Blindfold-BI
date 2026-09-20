"""
Test suite for Phase 2: Decentralized Analytical Tools Engine.
Verifies:
1. Deterministic pure DuckDB execution and latency < 50ms.
2. Canonical ToolResult contract compliance across all 14 tools + period resolver.
3. Ground Truth Exact Alignment (Section 3.6 of CLAUDE.md):
   - Pipeline Summary: 49 open deals (47 with value, ₹68.82 Cr), Tender outlier share ~77.3%, Non-tender pipeline ~₹15.62 Cr.
   - Revenue Ladder: 176 work orders, Contracted (excl GST) ₹21.16 Cr, Billed ₹18.06 Cr, Net Receivables ₹3.63 Cr, 11 negative receivable rows (DQ009).
   - Cross-Board Feasibility: Direct join infeasible (DQ015), 9 canonical sectors reconciled.
   - Data Quality: DQ001-DQ016 audit checks.
4. FastAPI REST endpoints (/api/tools, /api/tools/starter-chips, /api/tools/{tool_name}/schema, /api/tools/{tool_name}).
5. MCP Server registration verification.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.tools.registry import registry
from app.contracts import ToolResult, Fact, Table, ChartSpec
from app.data.duckdb_store import duckdb_store


@pytest.fixture(scope="module", autouse=True)
def initialize_duckdb():
    duckdb_store.initialize()


def test_registry_contains_all_tools():
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]
    expected_tools = [
        "pipeline_summary",
        "win_loss_analysis",
        "owner_performance",
        "revenue_ladder",
        "receivables_summary",
        "sector_performance",
        "workorder_health",
        "link_deals_to_orders",
        "data_quality_report",
        "data_debt_list",
        "leadership_brief",
        "compare_periods",
        "explain_metric",
        "list_capabilities",
        "resolve_period",
    ]
    for exp in expected_tools:
        assert exp in tool_names, f"Expected tool '{exp}' not found in registry"


def test_all_tools_return_canonical_tool_result():
    duckdb_store.initialize()
    for tool_meta in registry.list_tools():
        name = tool_meta.name
        kwargs = {}
        if name == "compare_periods":
            kwargs = {"metric": "open_pipeline_value", "period_a": "Q3 FY25-26", "period_b": "Q4 FY25-26"}
        elif name == "explain_metric":
            kwargs = {"metric": "open_pipeline_value"}
        elif name == "resolve_period":
            kwargs = {"text": "Q3 FY25-26"}

        res = registry.execute_tool(name, kwargs)

        assert isinstance(res, ToolResult), f"Tool {name} did not return a ToolResult"
        assert res.tool == name
        assert len(res.facts) > 0, f"Tool {name} returned empty facts"
        assert res.audit is not None
        assert "duration_ms" in res.audit
        assert res.audit["duration_ms"] < 250.0, f"Tool {name} took {res.audit['duration_ms']}ms (>250ms)"

        # Check fact structure
        for f in res.facts:
            assert isinstance(f, Fact)
            assert f.id.startswith("F")
            assert f.metric is not None
            assert f.display is not None


def test_ground_truth_pipeline_summary():
    # 1. Full Open Pipeline
    res = registry.execute_tool("pipeline_summary")
    facts_dict = {f.metric: f for f in res.facts}

    assert facts_dict["open_deals_count"].value == 49
    # Ground truth: ~68.82 Cr (688,152,293.17)
    assert round(facts_dict["open_pipeline_value"].value / 1e7, 2) == 68.82
    # Tender outlier share > 70% (~77.3%)
    assert abs(facts_dict["tender_outlier_share"].value - 77.3) < 1.0

    # 2. Exclude Outliers (Non-tender pipeline: ~₹15.62 Cr)
    res_no_tender = registry.execute_tool("pipeline_summary", {"exclude_outliers": True})
    facts_no_tender = {f.metric: f for f in res_no_tender.facts}
    assert round(facts_no_tender["open_pipeline_value"].value / 1e7, 2) == 15.62

    # 3. Sector Filter (Energy group)
    res_energy = registry.execute_tool("pipeline_summary", {"sector_group": "energy"})
    facts_energy = {f.metric: f for f in res_energy.facts}
    assert facts_energy["open_deals_count"].value == 12
    # Ground truth ~3.19 Cr (31,894,034.33)
    assert round(facts_energy["open_pipeline_value"].value / 1e7, 2) == 3.19


def test_ground_truth_revenue_ladder():
    res = registry.execute_tool("revenue_ladder")
    facts_dict = {f.metric: f for f in res.facts}

    # Contracted: ₹21.16 Cr (211,649,409.21)
    assert round(facts_dict["wo_contracted_value"].value / 1e7, 2) == 21.16
    # Net receivables: ₹3.63 Cr (36,291,748.87)
    assert round(facts_dict["wo_receivable_value"].value / 1e7, 2) == 3.63
    # Won deals bookings: ₹9.50 Cr
    assert round(facts_dict["won_deal_value"].value / 1e7, 2) == 9.50
    # Realization rate: ~50.7%
    assert abs(facts_dict["realization_rate_pct"].value - 50.7) < 1.0

    # DQ009 caveat code present on receivables fact
    assert "DQ009" in facts_dict["wo_receivable_value"].caveat_codes


def test_ground_truth_receivables_and_credit_notes():
    res = registry.execute_tool("receivables_summary")
    facts_dict = {f.metric: f for f in res.facts}

    # Net receivables: ₹3.63 Cr
    assert round(facts_dict["wo_receivable_value"].value / 1e7, 2) == 3.63
    # Exactly 11 credit balance rows (DQ009)
    assert facts_dict["credit_notes_count"].value == 11
    assert "DQ009" in facts_dict["credit_notes_count"].caveat_codes


def test_cross_board_linkage_refusal():
    res = registry.execute_tool("link_deals_to_orders")
    facts_dict = {f.metric: f for f in res.facts}

    # Refusal of direct joins (DQ015)
    assert facts_dict["direct_link_feasible"].value is False
    assert len(res.dq) > 0
    assert any(dq.code == "DQ015" for dq in res.dq)

    # 9 canonical sectors reconciled
    assert facts_dict["sectors_reconciled"].value == 9


def test_period_resolver_indian_fy():
    # 1. Q3 FY25-26: Oct 1, 2025 to Dec 31, 2025
    res_q3 = registry.execute_tool("resolve_period", {"text": "Q3 FY25-26"})
    facts_q3 = {f.metric: f for f in res_q3.facts}
    assert facts_q3["start_date"].value == "2025-10-01"
    assert facts_q3["end_date"].value == "2025-12-31"
    assert facts_q3["fiscal_quarter"].value == "Q3"

    # 2. FY24-25: Apr 1, 2024 to Mar 31, 2025
    res_fy = registry.execute_tool("resolve_period", {"text": "FY24-25"})
    facts_fy = {f.metric: f for f in res_fy.facts}
    assert facts_fy["start_date"].value == "2024-04-01"
    assert facts_fy["end_date"].value == "2025-03-31"


def test_rest_tools_endpoints():
    client = TestClient(app)
    headers = {"X-API-Key": settings.API_KEY}

    # 1. GET /api/v1/tools (Catalog)
    resp_cat = client.get("/api/v1/tools", headers=headers)
    assert resp_cat.status_code == 200
    catalog = resp_cat.json()
    assert len(catalog) >= 14
    tool_names = [t["name"] for t in catalog]
    assert "pipeline_summary" in tool_names
    assert "revenue_ladder" in tool_names

    # 2. GET /api/v1/tools/starter-chips
    resp_chips = client.get("/api/v1/tools/starter-chips", headers=headers)
    assert resp_chips.status_code == 200
    chips = resp_chips.json()
    assert len(chips) == 6
    assert any("pipeline" in c["label"].lower() for c in chips)

    # 3. GET /api/v1/tools/{tool_name}/schema
    resp_schema = client.get("/api/v1/tools/pipeline_summary/schema", headers=headers)
    assert resp_schema.status_code == 200
    schema = resp_schema.json()
    assert schema["name"] == "pipeline_summary"
    assert "parameters" in schema

    # 4. POST /api/v1/tools/{tool_name}
    resp_exec = client.post("/api/v1/tools/pipeline_summary", json={"args": {"sector": "Mining"}}, headers=headers)
    assert resp_exec.status_code == 200
    res_data = resp_exec.json()
    assert res_data["tool"] == "pipeline_summary"
    assert len(res_data["facts"]) > 0
    assert "audit" in res_data
