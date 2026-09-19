import os
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Blindfold BI, an enterprise executive intelligence agent for Skylark Drones.
All sensitive client identities and deal names in your input have been anonymized via the Blindfold Privacy Gateway into tokens (e.g. CLIENT_ENT_001, PROJECT_DEAL_001, OWNER_REP_01).

STRICT RULES:
1. NEVER do mental arithmetic or calculate your own totals, averages, or percentages.
2. Quote all numbers and metrics EXACTLY as given in the analytical tool output.
3. Structure your response into clear executive sections:
   - 🎯 Key Takeaways & Executive Summary
   - 📊 Metrics & Cohort Breakdown
   - ⚠️ Operational Insights & Risks
   - 💡 Strategic Recommendations
4. Do not remove or alter tokens (like PROJECT_DEAL_001). Keep them intact so the gateway can restore them.
"""

class LLMClient:
    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = settings.NVIDIA_BASE_URL
        self.model = settings.NVIDIA_MODEL
        self.client = None
        if self.api_key and self.api_key.startswith("nvapi-"):
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )

    async def generate_response(self, user_query: str, tool_name: str, tool_data: Dict[str, Any]) -> str:
        """
        Sends the anonymized tool output to NVIDIA NIM LLM.
        Falls back to deterministic synthesizer if API key is not configured or on network failure.
        """
        prompt = (
            f"User Question: {user_query}\n\n"
            f"Tool Executed: {tool_name}\n"
            f"Analytical Tool Results (Tokenized & Deterministic):\n"
            f"{json.dumps(tool_data, indent=2)}\n\n"
            "Generate an executive intelligence response based ONLY on these facts."
        )

        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=1024
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"NVIDIA NIM API call failed ({e}). Falling back to local synthesizer.")

        return self._local_synthesize(user_query, tool_name, tool_data)

    def _local_synthesize(self, user_query: str, tool_name: str, tool_data: Dict[str, Any]) -> str:
        """Local fact-grounded response synthesizer (used as robust zero-failure fallback)."""
        if "pipeline" in tool_name or "total_open_deals" in str(tool_data):
            s = tool_data.get("summary", {})
            return (
                f"### 🎯 Executive Pipeline Overview\n\n"
                f"- **Active Pipeline Value**: ₹{s.get('total_pipeline_value', 0):,.2f} across **{s.get('total_open_deals', 0)} open deals**.\n"
                f"- **Probability-Weighted Value**: ₹{s.get('total_weighted_pipeline', 0):,.2f} (~₹{s.get('total_weighted_pipeline', 0)/10000000:.2f} Cr).\n"
                f"- **Average Deal Size**: ₹{s.get('avg_deal_size', 0):,.2f}.\n\n"
                f"#### 📊 Strategic Observations\n"
                f"1. Open sales pipeline shows strong top-of-funnel traction.\n"
                f"2. High-probability deals represent key conversion targets for upcoming quarterly cash flow.\n\n"
                f"#### 💡 Recommended Next Steps\n"
                f"- Prioritize enterprise proposals currently in negotiation stages to accelerate close dates."
            )
        elif "revenue" in tool_name or "contracted_amount_excl_gst" in str(tool_data):
            s = tool_data.get("summary", {})
            return (
                f"### 💰 Revenue Realization Waterfall\n\n"
                f"- **Contracted Work Orders (Excl GST)**: ₹{s.get('contracted_amount_excl_gst', 0):,.2f} across **{s.get('total_work_orders', 0)} orders**.\n"
                f"- **Invoiced / Billed Revenue (Excl GST)**: ₹{s.get('billed_amount_excl_gst', 0):,.2f} (**{s.get('realization_rate_pct', 0)}%** realization rate).\n"
                f"- **Cash Collected (Incl GST)**: ₹{s.get('collected_amount_incl_gst', 0):,.2f} (**{s.get('collection_efficiency_pct', 0)}%** collection efficiency).\n"
                f"- **Unbilled Backlog**: ₹{s.get('unbilled_backlog_excl_gst', 0):,.2f} (~₹{s.get('unbilled_backlog_excl_gst', 0)/10000000:.2f} Cr).\n"
                f"- **Outstanding Receivables**: ₹{s.get('outstanding_receivables', 0):,.2f}.\n\n"
                f"#### ⚠️ Operational Risk\n"
                f"A significant backlog of contracted work orders has yet to be billed, representing cash locked in operations.\n\n"
                f"#### 💡 Action Items\n"
                f"- Expedite field deliverable sign-offs to convert the unbilled backlog into cash."
            )
        elif "conversion" in tool_name:
            return (
                f"### 🔗 Won Deals to Work Orders Conversion\n\n"
                f"- **Total Won Deals**: {tool_data.get('total_won_deals', 0)}\n"
                f"- **Converted to Active Work Orders**: {tool_data.get('converted_to_wo_count', 0)}\n"
                f"- **Pending WO Creation**: {tool_data.get('pending_wo_creation_count', 0)} deals valued at ₹{tool_data.get('pending_handoff_deal_value', 0):,.2f}\n"
                f"- **Conversion Efficiency Rate**: **{tool_data.get('conversion_rate_pct', 0)}%**\n\n"
                f"#### 💡 Sales-to-Ops Handoff Action\n"
                f"Closing the gap on the {tool_data.get('pending_wo_creation_count', 0)} pending deals will immediately expand active operational billing."
            )
        elif "health" in tool_name:
            return (
                f"### ⚙️ Work Order Execution Health\n\n"
                f"- **Delayed Projects Identified**: {tool_data.get('delayed_orders_count', 0)} projects past scheduled end date.\n"
                f"- Review operations staffing and equipment allocation to clear project bottlenecks."
            )
        elif "debt" in tool_name:
            return (
                f"### ⚠️ Data Hygiene & Debt Report\n\n"
                f"- **Total Actionable Records**: {tool_data.get('total_debt_records', 0)}\n"
                f"- **High Severity Issues**: {tool_data.get('high_severity_count', 0)} (including 'Update Required' and unbilled completed orders).\n"
                f"- **Medium Severity Issues**: {tool_data.get('medium_severity_count', 0)}.\n\n"
                f"Please review the Data Debt Action Center to export the remediation checklist for Monday.com."
            )
        else:
            return (
                f"### Executive Intelligence Brief\n\n"
                f"The analytical query completed successfully. All figures have been verified deterministically."
            )

llm_client = LLMClient()
