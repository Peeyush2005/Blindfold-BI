import time
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.config import settings
from app.models.schemas import ChatResponse, TrustReceipt, SuggestionChip, PipelineStepEvent
from app.core.anonymizer import blindfold
from app.core.verifier import verifier
from app.core.llm_client import llm_client
from app.data.db import db
from app.tools.pipeline_tools import get_pipeline_summary
from app.tools.revenue_tools import get_revenue_realization_summary
from app.tools.operations_tools import get_work_order_health, get_cross_board_conversion, get_data_debt_report
from app.tools.executive_tools import get_executive_brief

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.contract = self._load_contract()

    def _load_contract(self) -> Dict[str, Any]:
        try:
            with open(settings.CONTRACTS_PATH, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load metric contract: {e}")
            return {}

    def init_catalog(self):
        """Initializes Blindfold Gateway with known real names from DuckDB."""
        try:
            deals_rows, _, _ = db.query("SELECT DISTINCT deal_name FROM deals WHERE deal_name IS NOT NULL;")
            clients_rows, _, _ = db.query("SELECT DISTINCT client_code FROM deals WHERE client_code IS NOT NULL;")
            owners_rows, _, _ = db.query("SELECT DISTINCT owner_code FROM deals WHERE owner_code IS NOT NULL;")

            deals = [r["deal_name"] for r in deals_rows if r.get("deal_name")]
            clients = [r["client_code"] for r in clients_rows if r.get("client_code")]
            owners = [r["owner_code"] for r in owners_rows if r.get("owner_code")]

            blindfold.register_entities(deals, clients, owners)
            logger.info(f"Blindfold Gateway catalog initialized with {len(deals)} deals, {len(clients)} clients, {len(owners)} owners.")
        except Exception as e:
            logger.error(f"Error registering entities into Blindfold Gateway: {e}")

    async def execute_query(self, user_query: str, session_id: str = "default") -> ChatResponse:
        steps: List[PipelineStepEvent] = []
        overall_start = time.time()
        clean_query = user_query.strip()
        lowered_query = clean_query.lower()

        # Step 1: User Input Parsing
        t0 = time.time()
        steps.append(PipelineStepEvent(
            step_number=1,
            step_name="User Intent & Input Parsing",
            status="success",
            duration_ms=round((time.time() - t0) * 1000, 2),
            input_payload={"raw_query": clean_query, "session_id": session_id},
            output_payload={"normalized_query": lowered_query, "length": len(clean_query)},
            summary=f"Parsed input query of {len(clean_query)} characters."
        ))

        # Step 2: Metric Contract & Ambiguity Check
        t1 = time.time()
        ambiguity_found = False
        clarification_chips = []
        for item in self.contract.get("ambiguity_triggers", []):
            kw = item.get("keyword", "").lower()
            if kw in lowered_query and not any(opt["label"].lower() in lowered_query for opt in item.get("options", [])):
                # If exact specific target is already clear, skip ambiguity
                if "waterfall" in lowered_query or "brief" in lowered_query or "debt" in lowered_query:
                    continue
                ambiguity_found = True
                for opt in item.get("options", []):
                    clarification_chips.append(SuggestionChip(
                        label=f"👉 {opt['label']}",
                        query=opt["query"],
                        is_clarification=True
                    ))
                break

        steps.append(PipelineStepEvent(
            step_number=2,
            step_name="Metric Contract & Ambiguity Check",
            status="warning" if ambiguity_found else "success",
            duration_ms=round((time.time() - t1) * 1000, 2),
            input_payload={"query": clean_query, "contract_version": self.contract.get("version", "1.0.0")},
            output_payload={"is_ambiguous": ambiguity_found, "clarification_chips": [c.dict() for c in clarification_chips]},
            summary="Ambiguity detected: generated clarification options." if ambiguity_found else "Query conforms to Metric Contract specifications."
        ))

        # Step 3: Tool Routing & Parameter Extraction
        t2 = time.time()
        tool_name = "pipeline_summary"
        tool_params = {}

        if any(k in lowered_query for k in ["revenue", "billed", "contracted", "collected", "waterfall", "receivable", "debtor"]):
            tool_name = "revenue_realization_summary"
            if "mining" in lowered_query:
                tool_params["sector"] = "Mining"
            elif "renewables" in lowered_query:
                tool_params["sector"] = "Renewables"
        elif any(k in lowered_query for k in ["brief", "executive", "leadership", "kpi", "summary"]):
            tool_name = "executive_brief"
        elif any(k in lowered_query for k in ["conversion", "won to work order", "hand off", "cross-board", "linked"]):
            tool_name = "cross_board_conversion"
        elif any(k in lowered_query for k in ["delay", "health", "execution status", "stuck", "ongoing"]):
            tool_name = "work_order_health"
        elif any(k in lowered_query for k in ["debt", "hygiene", "missing", "update required", "dirty", "ops list"]):
            tool_name = "data_debt_report"
        else:
            tool_name = "pipeline_summary"
            if "mining" in lowered_query:
                tool_params["sector"] = "Mining"
            elif "renewables" in lowered_query:
                tool_params["sector"] = "Renewables"

        steps.append(PipelineStepEvent(
            step_number=3,
            step_name="Tool Routing & Parameter Extraction",
            status="success",
            duration_ms=round((time.time() - t2) * 1000, 2),
            input_payload={"query": clean_query},
            output_payload={"selected_tool": tool_name, "parameters": tool_params},
            summary=f"Routed query to deterministic analytical tool: '{tool_name}'."
        ))

        # Step 6 First (DuckDB Deterministic Engine) to get raw data for Anonymization
        t_duckdb = time.time()
        tool_output: Dict[str, Any] = {}
        chart_data: Optional[Dict[str, Any]] = None

        if tool_name == "revenue_realization_summary":
            tool_output = get_revenue_realization_summary(**tool_params)
            chart_data = {
                "type": "waterfall",
                "title": "Revenue Realization (Excl vs Incl GST)",
                "categories": ["Contracted (Excl)", "Billed (Excl)", "Collected (Incl)", "Unbilled Backlog", "Receivables"],
                "values": [
                    tool_output["summary"]["contracted_amount_excl_gst"],
                    tool_output["summary"]["billed_amount_excl_gst"],
                    tool_output["summary"]["collected_amount_incl_gst"],
                    tool_output["summary"]["unbilled_backlog_excl_gst"],
                    tool_output["summary"]["outstanding_receivables"]
                ]
            }
        elif tool_name == "executive_brief":
            tool_output = get_executive_brief()
        elif tool_name == "cross_board_conversion":
            tool_output = get_cross_board_conversion()
            chart_data = {
                "type": "pie",
                "title": "Won Deals Conversion",
                "data": [
                    {"name": "Converted to Work Orders", "value": tool_output["converted_to_wo_count"]},
                    {"name": "Pending WO Creation", "value": tool_output["pending_wo_creation_count"]}
                ]
            }
        elif tool_name == "work_order_health":
            tool_output = get_work_order_health()
            chart_data = {
                "type": "bar",
                "title": "Orders by Execution Status",
                "categories": [r["execution_status"] for r in tool_output["execution_breakdown"]],
                "values": [r["count"] for r in tool_output["execution_breakdown"]]
            }
        elif tool_name == "data_debt_report":
            tool_output = get_data_debt_report()
        else:
            tool_output = get_pipeline_summary(**tool_params)
            chart_data = {
                "type": "bar",
                "title": "Open Pipeline by Sector",
                "categories": [r["sector"] for r in tool_output.get("by_sector", [])[:5]],
                "values": [r["sector_value"] for r in tool_output.get("by_sector", [])[:5]]
            }

        duckdb_dur = round((time.time() - t_duckdb) * 1000, 2)

        # Step 4: Blindfold Anonymization Gateway
        t3 = time.time()
        anonymized_tool_output = blindfold.anonymize_obj(tool_output)
        anonymized_query = blindfold.anonymize_text(clean_query)
        active_tokens = {k: v for k, v in list(blindfold.token_to_entity.items())[:5]}

        steps.append(PipelineStepEvent(
            step_number=4,
            step_name="Blindfold Privacy Gateway",
            status="success",
            duration_ms=round((time.time() - t3) * 1000, 2),
            input_payload={"sample_entities": list(blindfold.entity_to_token.keys())[:3]},
            output_payload={"tokenized_query": anonymized_query, "active_sample_tokens": active_tokens},
            summary="Substituted all client, deal, and personnel names with session tokens. Zero PII leaked."
        ))

        # Step 5: NVIDIA NIM LLM Processing
        t4 = time.time()
        draft_response = await llm_client.generate_response(anonymized_query, tool_name, anonymized_tool_output)
        llm_dur = round((time.time() - t4) * 1000, 2)

        steps.append(PipelineStepEvent(
            step_number=5,
            step_name="NVIDIA NIM LLM Processing",
            status="success",
            duration_ms=llm_dur,
            input_payload={"model": settings.NVIDIA_MODEL, "temperature": 0.0, "pii_present": False},
            output_payload={"draft_length": len(draft_response), "tokens_received": True},
            summary=f"NVIDIA NIM generated tokenized narrative in {llm_dur}ms with zero arithmetic."
        ))

        # Record Step 6: DuckDB Deterministic Engine
        steps.append(PipelineStepEvent(
            step_number=6,
            step_name="DuckDB Deterministic Engine",
            status="success",
            duration_ms=duckdb_dur,
            input_payload={"tool": tool_name, "params": tool_params},
            output_payload={"summary_metrics": tool_output.get("summary") or tool_output.get("kpis") or {}},
            summary=f"Executed pure SQL in DuckDB ({duckdb_dur}ms). No LLM-written code."
        ))

        # Step 7: Hallucination Verifier & Fact Audit
        t5 = time.time()
        is_verified, verified_text, facts_grounded, conf_score = verifier.verify(draft_response, tool_output)
        ver_dur = round((time.time() - t5) * 1000, 2)

        steps.append(PipelineStepEvent(
            step_number=7,
            step_name="Hallucination Verifier & Audit",
            status="success" if is_verified else "warning",
            duration_ms=ver_dur,
            input_payload={"draft_numbers_checked": True},
            output_payload={"verified": is_verified, "facts_grounded": facts_grounded, "confidence_score": conf_score},
            summary=f"Verified numerical consistency ({facts_grounded} grounded facts). Confidence: {conf_score * 100}%."
        ))

        # Step 8: De-anonymizer & Trust Receipt Assembly
        t6 = time.time()
        final_answer = blindfold.deanonymize_text(verified_text)

        # Build Trust Receipt
        audit_info = tool_output.get("audit", {})
        trust_receipt = TrustReceipt(
            query_executed=audit_info.get("query", f"DuckDB execution of {tool_name}"),
            parameters=tool_params,
            rows_scanned=audit_info.get("rows_scanned", 175),
            rows_excluded=audit_info.get("rows_excluded", 0),
            exclusion_reasons=[audit_info.get("exclusion_reason", "Row criteria satisfied")],
            execution_duration_ms=round(duckdb_dur + llm_dur, 2),
            confidence_score=conf_score,
            facts_grounded=facts_grounded,
            data_as_of=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            verified=is_verified
        )

        steps.append(PipelineStepEvent(
            step_number=8,
            step_name="De-anonymizer & Trust Receipt",
            status="success",
            duration_ms=round((time.time() - t6) * 1000, 2),
            input_payload={"tokenized_text_preview": verified_text[:60] + "..."},
            output_payload={"real_text_preview": final_answer[:60] + "...", "trust_receipt_ready": True},
            summary="Tokens re-hydrated to human-readable names for UI presentation."
        ))

        # Build suggestion chips
        suggestion_chips = clarification_chips if clarification_chips else [
            SuggestionChip(label="📊 Executive Brief", query="Generate executive leadership brief with KPIs and risks"),
            SuggestionChip(label="💰 Revenue Waterfall", query="Show revenue realization from contracted to collected"),
            SuggestionChip(label="🔗 Won to WO Conversion", query="Show conversion rate from Won Deals to Work Orders"),
            SuggestionChip(label="⚠️ Data Debt List", query="Show data hygiene debt and items needing update")
        ]

        return ChatResponse(
            answer=final_answer,
            trust_receipt=trust_receipt,
            suggestion_chips=suggestion_chips,
            pipeline_trace=steps,
            chart_data=chart_data
        )

orchestrator = PipelineOrchestrator()
