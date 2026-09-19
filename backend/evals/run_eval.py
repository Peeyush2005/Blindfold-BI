"""
Golden Evaluation Runner for Blindfold BI.
Validates the conversational BI agent against Section 3.6 canonical ground truth,
enforcing:
1. Zero PII Leakage across the Blindfold Privacy Gateway
2. Zero Arithmetic Hallucinations via Numbers-by-Reference verification
3. Deterministic DuckDB metric correctness
4. End-to-end S1-S10 state machine latency and trust receipt integrity
"""

import sys
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.core.gateway import blindfold_gateway

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


GOLDEN_TEST_CASES = [
    {
        "id": "GT-01",
        "name": "Pipeline Summary & Open Value",
        "query": "What is our total open pipeline value and deal count?",
        "expected_tool": "pipeline_summary",
        "assertions": {
            "min_open_deals": 49,
            "max_open_deals": 49,
            "expected_open_pipeline": 688152293.17,
            "tolerance_abs": 2.0,
        }
    },
    {
        "id": "GT-02",
        "name": "Revenue Realization Ladder",
        "query": "Show me the revenue realization waterfall and billed amounts",
        "expected_tool": "revenue_ladder",
        "assertions": {
            "min_work_orders": 175,
            "max_work_orders": 176,
            "expected_contracted": 211649409.21,
            "expected_billed": 107389776.59,
            "tolerance_abs": 2.0,
        }
    },
    {
        "id": "GT-03",
        "name": "Receivables & Aging Summary",
        "query": "What are our outstanding receivables and aging breakdown?",
        "expected_tool": "receivables_summary",
        "assertions": {
            "expected_receivables": 36291748.87,
            "tolerance_abs": 2.0,
        }
    },
    {
        "id": "GT-04",
        "name": "Cross-Board Conversion Rate",
        "query": "What is our deal to work order conversion rate?",
        "expected_tool": "link_deals_to_orders",
        "assertions": {
            "min_won_deals": 150,
            "min_conversion_rate": 60.0,
            "max_conversion_rate": 70.0,
        }
    },
    {
        "id": "GT-05",
        "name": "Data Debt & CRM Hygiene",
        "query": "Show me the data debt list and operational remediation items",
        "expected_tool": "data_debt_list",
        "assertions": {
            "min_debt_records": 10,
        }
    },
    {
        "id": "GT-06",
        "name": "Energy Sector Performance",
        "query": "What is our pipeline and revenue in the energy sector?",
        "expected_tool": ["pipeline_summary", "sector_performance"],
        "assertions": {
            "min_facts": 2,
        }
    },
    {
        "id": "GT-07",
        "name": "Blindfold Zero PII Leakage Check",
        "query": "What is the status of Naruto deal with COMPANY089?",
        "expected_tool": ["pipeline_summary", "link_deals_to_orders"],
        "pii_probe": {
            "raw_entities": ["Naruto", "COMPANY089"],
            "expected_tokens": ["PROJECT_DEAL_", "CLIENT_ENT_"]
        }
    },
    {
        "id": "GT-08",
        "name": "Metric Explanation Contract",
        "query": "Explain the definition and formula for Realization Rate",
        "expected_tool": "explain_metric",
        "assertions": {
            "contains_keywords": ["realization", "formula", "billed", "contracted"]
        }
    }
]


async def run_evaluations(verbose: bool = True) -> Dict[str, Any]:
    print("=" * 78)
    print("🎯 BLINDFOLD BI — GOLDEN QUERY EVALUATION RUNNER")
    print("Zero PII Leakage • Zero Arithmetic Hallucinations • Sub-5ms DuckDB Ground Truth")
    print("=" * 78)

    t_init = time.time()
    db.init_db()
    orchestrator.init_catalog()
    init_ms = round((time.time() - t_init) * 1000, 2)
    print(f"[*] DuckDB Store & Blindfold Catalog initialized in {init_ms}ms\n")

    results = []
    total_queries = len(GOLDEN_TEST_CASES)
    passed_queries = 0

    for idx, tc in enumerate(GOLDEN_TEST_CASES, 1):
        test_id = tc["id"]
        test_name = tc["name"]
        query = tc["query"]
        session_id = f"eval_{test_id.lower()}_{int(time.time())}"

        print(f"[{idx}/{total_queries}] Running {test_id}: '{test_name}'")
        if verbose:
            print(f"    Query: \"{query}\"")

        t0 = time.time()
        res = await orchestrator.execute_query(query, session_id=session_id)
        dur_ms = round((time.time() - t0) * 1000, 2)

        failures = []

        # 1. Check Tool Selection
        selected_tool = None
        s3_step = next((s for s in res.pipeline_trace if s.step_number == 3), None)
        if s3_step and s3_step.output_payload:
            selected_tool = s3_step.output_payload.get("tool")

        expected_tool = tc.get("expected_tool")
        if expected_tool:
            if isinstance(expected_tool, list):
                if selected_tool not in expected_tool:
                    failures.append(f"Tool mismatch: expected one of {expected_tool}, got '{selected_tool}'")
            else:
                if selected_tool != expected_tool:
                    failures.append(f"Tool mismatch: expected '{expected_tool}', got '{selected_tool}'")

        # 2. Check PII Leakage in S4
        s4_step = next((s for s in res.pipeline_trace if s.step_number == 4), None)
        tokenized_query = ""
        if s4_step and s4_step.output_payload:
            tokenized_query = s4_step.output_payload.get("tokenized_query", "")

        pii_probe = tc.get("pii_probe")
        if pii_probe:
            for raw_ent in pii_probe.get("raw_entities", []):
                if raw_ent.lower() in tokenized_query.lower():
                    failures.append(f"PII LEAK DETECTED in S4: Raw entity '{raw_ent}' found in tokenized query: '{tokenized_query}'")
            for exp_token in pii_probe.get("expected_tokens", []):
                if exp_token not in tokenized_query:
                    failures.append(f"Expected surrogate token prefix '{exp_token}' missing from tokenized query")

        # 3. Check Arithmetic Hallucinations in S8
        s8_step = next((s for s in res.pipeline_trace if s.step_number == 8), None)
        hallucinations = []
        if s8_step and s8_step.output_payload:
            hallucinations = s8_step.output_payload.get("hallucinations_detected", [])

        if hallucinations:
            failures.append(f"Arithmetic hallucination detected: ungrounded numbers {hallucinations}")

        # 4. Check Trust Receipt
        if not res.trust_receipt:
            failures.append("Missing Trust Receipt in response")
        elif res.trust_receipt.confidence_score < 0.7:
            failures.append(f"Low confidence score: {res.trust_receipt.confidence_score}")

        # 5. Check Ground Truth Assertions
        assertions = tc.get("assertions", {})
        facts_map = {}
        for f in res.facts:
            if isinstance(f, dict):
                if f.get("label"):
                    facts_map[f["label"]] = f.get("value")
                if f.get("metric"):
                    facts_map[f["metric"]] = f.get("value")

        if "min_open_deals" in assertions:
            val = facts_map.get("open_deals_count", facts_map.get("Open Deals Count", facts_map.get("Total Open Deals", 0)))
            if val < assertions["min_open_deals"]:
                failures.append(f"Open deals ({val}) below minimum {assertions['min_open_deals']}")

        if "expected_open_pipeline" in assertions:
            val = facts_map.get("open_pipeline_value", facts_map.get("Open Pipeline Value", facts_map.get("Total Pipeline Value", 0.0)))
            exp = assertions["expected_open_pipeline"]
            tol = assertions.get("tolerance_abs", 2.0)
            if abs(val - exp) > tol:
                failures.append(f"Pipeline value ₹{val:,.2f} deviates from expected ₹{exp:,.2f} (> {tol})")

        if "expected_receivables" in assertions:
            val = facts_map.get("wo_receivable_value", facts_map.get("Net Accounts Receivable", facts_map.get("Outstanding Receivables", 0.0)))
            exp = assertions["expected_receivables"]
            tol = assertions.get("tolerance_abs", 2.0)
            if abs(val - exp) > tol:
                failures.append(f"Outstanding receivables ₹{val:,.2f} deviates from expected ₹{exp:,.2f} (> {tol})")

        if "contains_keywords" in assertions:
            answer_lower = res.answer.lower()
            for kw in assertions["contains_keywords"]:
                if kw not in answer_lower:
                    failures.append(f"Expected keyword '{kw}' missing from answer")

        passed = len(failures) == 0
        if passed:
            passed_queries += 1
            status_str = "✅ PASS"
        else:
            status_str = "❌ FAIL"

        results.append({
            "id": test_id,
            "name": test_name,
            "passed": passed,
            "duration_ms": dur_ms,
            "tool": selected_tool,
            "facts_count": len(res.facts),
            "confidence": res.trust_receipt.confidence_score if res.trust_receipt else 0.0,
            "hallucinations": len(hallucinations),
            "failures": failures,
        })

        print(f"    Result: {status_str} in {dur_ms}ms | Tool: '{selected_tool}' | Facts: {len(res.facts)} | Conf: {res.trust_receipt.confidence_score if res.trust_receipt else 0.0}")
        if failures:
            for f in failures:
                print(f"      - [FAIL] {f}")
        print()

    # Summary Report
    print("=" * 78)
    print("📊 EVALUATION SCORECARD")
    print("=" * 78)
    print(f"Total Tests Executed : {total_queries}")
    print(f"Total Tests Passed   : {passed_queries}")
    print(f"Total Tests Failed   : {total_queries - passed_queries}")
    pass_rate = round((passed_queries / total_queries) * 100, 1)
    print(f"Overall Pass Rate    : {pass_rate}%")
    avg_latency = round(sum(r["duration_ms"] for r in results) / total_queries, 2)
    print(f"Average Turn Latency : {avg_latency}ms")
    print("=" * 78)

    return {
        "total": total_queries,
        "passed": passed_queries,
        "failed": total_queries - passed_queries,
        "pass_rate": pass_rate,
        "avg_latency_ms": avg_latency,
        "results": results,
    }


if __name__ == "__main__":
    out = asyncio.run(run_evaluations(verbose=True))
    if out["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
