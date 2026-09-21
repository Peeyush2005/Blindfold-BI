"""
Central Analytical Tool Registry for Blindfold BI.
Exposes 14 pure DuckDB deterministic tools across three consumption surfaces:
1. Python in-process dispatch (for the agent orchestrator)
2. REST endpoints (POST /api/tools/{tool_name}, GET /api/tools, etc.)
3. FastMCP / MCPServer definition (for /mcp endpoint)
"""

import inspect
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.contracts import ToolResult, ChipCandidate
from app.tools.chips import get_starter_chips, generate_followup_chips
from app.tools.pipeline_tools import (
    pipeline_summary,
    win_loss_analysis,
    owner_performance,
    deal_slippage,
    conversion_velocity,
)
from app.tools.revenue_tools import (
    revenue_ladder,
    revenue_waterfall,
    receivables_summary,
    sector_performance,
    credit_risk,
    aging_analysis,
    client_concentration,
    collection_efficiency,
)
from app.tools.operations_tools import (
    workorder_health,
    link_deals_to_orders,
    cross_board_linkage,
    unbilled_exposure,
    margin_analysis,
    reconciliation_ledger,
)
from app.tools.query_tools import (
    data_quality_report,
    data_debt_list,
    data_debt_ledger,
)
from app.tools.executive_tools import (
    leadership_brief,
    compare_periods,
    explain_metric,
    list_capabilities,
)
from app.tools.period_resolver import resolve_period

# FastMCP / MCPServer compatibility
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None


@dataclass
class ToolDefinition:
    name: str
    func: Callable[..., ToolResult]
    domain: str
    description: str
    signature: inspect.Signature = field(init=False)
    parameters_schema: Dict[str, Any] = field(init=False)

    def __post_init__(self):
        self.signature = inspect.signature(self.func)
        properties = {}
        required = []
        for param_name, param in self.signature.parameters.items():
            if param_name in ["self", "cls"]:
                continue
            prop_type = "string"
            if param.annotation is int:
                prop_type = "integer"
            elif param.annotation is float:
                prop_type = "number"
            elif param.annotation is bool:
                prop_type = "boolean"
            elif param.annotation is list or param.annotation == List[str]:
                prop_type = "array"

            properties[param_name] = {
                "type": prop_type,
                "default": param.default if param.default is not inspect.Parameter.empty else None,
            }
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        self.parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }


TOOL_EXAMPLES: Dict[str, List[str]] = {
    # 14 Canonical Business Tools
    "pipeline_summary": [
        "How's our pipeline looking for the energy sector this quarter?",
        "What is the open pipeline for energy in Q4 FY25-26?",
    ],
    "revenue_waterfall": [
        "Show me the complete revenue waterfall from bookings to cash collected",
        "What did we bill and collect against contracted value?",
    ],
    "sector_performance": [
        "Which sector has the biggest open pipeline?",
        "Rank sectors by open pipeline value and realization",
    ],
    "data_debt_ledger": [
        "Show me the actionable data debt ledger",
        "What data hygiene anomalies require operational remediation?",
    ],
    "credit_risk": [
        "What is our credit risk exposure across top debtors?",
        "Identify high-risk receivables and negative balance credit notes",
    ],
    "aging_analysis": [
        "Show aging schedule for overdue accounts receivable",
        "How much receivables balance is past 90 days overdue?",
    ],
    "client_concentration": [
        "What is our client concentration risk?",
        "Show top 10 clients by contracted value and Pareto share",
    ],
    "deal_slippage": [
        "How much pipeline has slipped past expected close date?",
        "Identify stale deals and slippage risk (DQ005)",
    ],
    "collection_efficiency": [
        "What is our cash collection rate and estimated DSO?",
        "How efficiently are we collecting against invoiced revenue?",
    ],
    "margin_analysis": [
        "What are our operational delivery realization rates across sectors?",
        "Analyze contracted versus billed realization by industry",
    ],
    "conversion_velocity": [
        "What is our historical commercial win rate?",
        "Show pipeline conversion progression from lead to won booking",
    ],
    "unbilled_exposure": [
        "What is our total unbilled operational exposure?",
        "How many completed work orders remain unbilled (DQ010)?",
    ],
    "reconciliation_ledger": [
        "Show cross-board financial reconciliation across Deals and Work Orders",
        "Reconcile CRM won bookings with operational contracted values",
    ],
    "cross_board_linkage": [
        "Can we link CRM deals to operational work orders?",
        "Explain cross-board linkage feasibility and sector bridge (DQ015)",
    ],
    # Additional specialized tools
    "win_loss_analysis": [
        "What is our historical win rate across sectors?",
        "Show win-loss breakdown for renewables deals",
    ],
    "owner_performance": [
        "How are deal owners performing across pipeline stages?",
        "Show pipeline distribution by sales owner",
    ],
    "revenue_ladder": [
        "What did we bill against contracted value?",
        "Show me the revenue realization ladder",
    ],
    "receivables_summary": [
        "How much cash have we collected?",
        "What is our outstanding receivables balance?",
    ],
    "workorder_health": [
        "Which work orders are still ongoing?",
        "How many work orders are currently active?",
    ],
    "link_deals_to_orders": [
        "Can we join deals and work orders?",
        "Show linkage between CRM deals and operational orders",
    ],
    "data_quality_report": [
        "How healthy is our data?",
        "What data quality issues exist in our CRM?",
    ],
    "data_debt_list": [
        "Show me the data quality ledger",
        "List all data anomalies by severity code",
    ],
    "leadership_brief": [
        "Generate executive leadership brief",
        "Summarize key business risks and recommendations",
    ],
    "compare_periods": [
        "Compare pipeline performance between quarters",
        "Show quarter-over-quarter revenue progression",
    ],
    "explain_metric": [
        "Explain how open pipeline is calculated",
        "What is the definition and formula for weighted pipeline?",
    ],
    "list_capabilities": [
        "What can this BI agent do?",
        "List all available analytical capabilities",
    ],
    "resolve_period": [
        "What are the date boundaries for Q4 FY25-26?",
        "Resolve current fiscal quarter range",
    ],
}


class ToolCallRequest(BaseModel):
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool function")


class ToolMetadata(BaseModel):
    name: str
    domain: str
    description: str
    parameters: Dict[str, Any]
    examples: List[str] = Field(default_factory=list)


class ToolRegistry:
    """Central registry and dispatch engine for all Blindfold BI analytical tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._mcp_server = FastMCP("blindfold-bi") if FastMCP is not None else None
        self._register_all_tools()

    def register(self, name: str, func: Callable[..., ToolResult], domain: str, description: Optional[str] = None):
        desc = description or (func.__doc__ or "").strip().split("\n")[0]
        tool_def = ToolDefinition(
            name=name,
            func=func,
            domain=domain,
            description=desc,
        )
        self._tools[name] = tool_def

        # Register on FastMCP server if available
        if self._mcp_server is not None:
            # Wrap function to return serializable dict for MCP clients
            @self._mcp_server.tool(name=name, description=desc)
            def _mcp_wrapper(**kwargs) -> Dict[str, Any]:
                res = func(**kwargs)
                return res.model_dump()

    def _register_all_tools(self):
        # =====================================================================
        # CANONICAL 14 BUSINESS TOOLS (MASTER PROMPT SPECIFICATION)
        # =====================================================================

        # 1. pipeline_summary
        self.register(
            "pipeline_summary",
            pipeline_summary,
            "Pipeline",
            "Open pipeline value, probability-weighted pipeline, stage distribution, and tender concentration.",
        )

        # 2. revenue_waterfall
        self.register(
            "revenue_waterfall",
            revenue_waterfall,
            "Revenue",
            "Complete revenue realization waterfall: Won Bookings -> Contracted -> Billed -> Collected -> Net Receivables.",
        )

        # 3. sector_performance
        self.register(
            "sector_performance",
            sector_performance,
            "Revenue",
            "Multi-board comparative analysis across canonical sectors, reconciling Deals funnel and Work Orders execution.",
        )

        # 4. data_debt_ledger
        self.register(
            "data_debt_ledger",
            data_debt_ledger,
            "Governance",
            "Actionable data debt and hygiene ledger (DQ001-DQ016) with affected records and remediation actions.",
        )

        # 5. credit_risk
        self.register(
            "credit_risk",
            credit_risk,
            "Revenue",
            "Accounts receivable credit risk, top exposed debtors by client token, and negative receivables / credit notes (DQ009).",
        )

        # 6. aging_analysis
        self.register(
            "aging_analysis",
            aging_analysis,
            "Revenue",
            "Accounts receivable aging schedule broken into 0-30, 31-60, 61-90, and 90+ days overdue buckets.",
        )

        # 7. client_concentration
        self.register(
            "client_concentration",
            client_concentration,
            "Revenue",
            "Pareto and client concentration analysis identifying revenue risk across top customer accounts.",
        )

        # 8. deal_slippage
        self.register(
            "deal_slippage",
            deal_slippage,
            "Pipeline",
            "Pipeline slippage and stale deal analysis (DQ005): Open deals whose expected close date has expired.",
        )

        # 9. collection_efficiency
        self.register(
            "collection_efficiency",
            collection_efficiency,
            "Revenue",
            "Cash collection rate (collected vs billed) and Days Sales Outstanding (DSO) efficiency metric.",
        )

        # 10. margin_analysis
        self.register(
            "margin_analysis",
            margin_analysis,
            "Operations",
            "Sector-level billing realization rates and operational delivery conversion margins.",
        )

        # 11. conversion_velocity
        self.register(
            "conversion_velocity",
            conversion_velocity,
            "Pipeline",
            "Commercial conversion velocity, historical win rates, and pipeline stage progression.",
        )

        # 12. unbilled_exposure
        self.register(
            "unbilled_exposure",
            unbilled_exposure,
            "Operations",
            "Unbilled revenue exposure and unbilled backlog, highlighting completed-but-unbilled projects (DQ010).",
        )

        # 13. reconciliation_ledger
        self.register(
            "reconciliation_ledger",
            reconciliation_ledger,
            "Operations",
            "Multi-stage commercial reconciliation across Deals, Work Orders, Billing Invoices, and Cash Collections.",
        )

        # 14. cross_board_linkage
        self.register(
            "cross_board_linkage",
            cross_board_linkage,
            "Operations",
            "Cross-board linkage feasibility audit (DQ015) enforcing canonical sector-level aggregation.",
        )

        # =====================================================================
        # COMPATIBILITY ALIASES & ADDITIONAL EXECUTIVE TOOLS
        # =====================================================================
        self.register(
            "revenue_ladder",
            revenue_ladder,
            "Revenue",
            "Complete revenue realization waterfall (alias for revenue_waterfall).",
        )
        self.register(
            "receivables_summary",
            receivables_summary,
            "Revenue",
            "Accounts receivable aging, top debtors by client token, and credit notes / negative receivables (DQ009).",
        )
        self.register(
            "win_loss_analysis",
            win_loss_analysis,
            "Pipeline",
            "Historical deal conversion rates (Won vs Lost vs Open) segmented by sector, owner, or product.",
        )
        self.register(
            "owner_performance",
            owner_performance,
            "Pipeline",
            "Commercial owner workload, open pipeline distribution, and unassigned deals (DQ004).",
        )
        self.register(
            "workorder_health",
            workorder_health,
            "Operations",
            "Execution status of Work Orders, overdue delivery dates (DQ011), and completed-but-unbilled projects (DQ010).",
        )
        self.register(
            "work_order_health",
            workorder_health,
            "Operations",
            "Execution status of Work Orders (alias).",
        )
        self.register(
            "link_deals_to_orders",
            link_deals_to_orders,
            "Operations",
            "Cross-board linkage feasibility audit (DQ015) enforcing sector-level reconciliation (alias for cross_board_linkage).",
        )
        self.register(
            "data_quality_report",
            data_quality_report,
            "Governance",
            "Comprehensive Data Quality and Hygiene Scorecard covering DQ001-DQ016 across both boards.",
        )
        self.register(
            "data_debt_list",
            data_debt_list,
            "Governance",
            "Granular remediation ledger for data hygiene anomalies with actionable advice and CSV export.",
        )
        self.register(
            "leadership_brief",
            leadership_brief,
            "Executive",
            "Consolidated executive leadership brief synthesizing pipeline, revenue, operations backlog, and data quality.",
        )
        self.register(
            "compare_periods",
            compare_periods,
            "Executive",
            "Period-over-period delta and percentage growth analysis between two Indian Fiscal Year periods.",
        )
        self.register(
            "explain_metric",
            explain_metric,
            "Executive",
            "Authoritative metric governance specification, SQL definition, and business logic from contracts.",
        )
        self.register(
            "list_capabilities",
            list_capabilities,
            "Executive",
            "Full catalog of deterministic analytical tools, data sources, and governance policies.",
        )
        self.register(
            "resolve_period",
            resolve_period,
            "Utility",
            "Parses natural-language fiscal period expressions into Indian Fiscal Year date boundaries and SQL filters.",
        )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        return [
            ToolMetadata(
                name=t.name,
                domain=t.domain,
                description=t.description,
                parameters=t.parameters_schema,
                examples=TOOL_EXAMPLES.get(t.name, []),
            )
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Executes a registered analytical tool by name with arguments.
        Returns a typed ToolResult.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry. Available tools: {list(self._tools.keys())}")

        tool_def = self._tools[name]
        call_args = args or {}

        # Filter call_args to match the function's signature
        sig = inspect.signature(tool_def.func)
        has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if not has_varkw:
            filtered_args = {k: v for k, v in call_args.items() if k in sig.parameters}
        else:
            filtered_args = call_args

        res = tool_def.func(**filtered_args)
        if hasattr(res, "tool") and res.tool != name:
            res.tool = name
        return res

    @property
    def mcp_server(self):
        return self._mcp_server


# Singleton instance
registry = ToolRegistry()
execute_tool = registry.execute_tool


# -------------------------------------------------------------------------
# FastAPI REST Router for Analytical Tools
# -------------------------------------------------------------------------

tools_router = APIRouter(prefix="/api/tools", tags=["Analytical Tools"])


@tools_router.get("", response_model=List[ToolMetadata])
def get_tools_catalog():
    """Lists all registered deterministic analytical tools and their parameter schemas."""
    return registry.list_tools()


@tools_router.get("/starter-chips", response_model=List[ChipCandidate])
def get_starter_suggestion_chips():
    """Returns the 6 canonical empty-state starter suggestion chips (Section 10.4)."""
    return get_starter_chips()


@tools_router.get("/{tool_name}/schema")
def get_tool_schema(tool_name: str):
    """Returns parameter schema and description for a specific tool."""
    tool_def = registry.get_tool(tool_name)
    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return {
        "name": tool_def.name,
        "domain": tool_def.domain,
        "description": tool_def.description,
        "parameters": tool_def.parameters_schema,
    }


@tools_router.post("/{tool_name}", response_model=ToolResult)
def run_tool_endpoint(tool_name: str, request: ToolCallRequest = Body(default_factory=ToolCallRequest)):
    """
    Executes an analytical tool deterministically via REST.
    Returns the complete ToolResult with facts, tables, charts, and trust receipt.
    """
    if not registry.get_tool(tool_name):
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    try:
        result = registry.execute_tool(tool_name, request.args)
        return result
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid arguments for tool '{tool_name}': {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing tool '{tool_name}': {str(e)}")
