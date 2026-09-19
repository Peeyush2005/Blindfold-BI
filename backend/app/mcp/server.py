"""
Model Context Protocol (MCP) Server for Blindfold BI.
Exposes Skylark Drones privacy-first analytical tools to Claude, Cursor, and enterprise agent clients.
"""

import sys
import json
import asyncio
from typing import Any, Dict, List

from app.data.db import db
from app.core.orchestrator import orchestrator
from app.core.anonymizer import blindfold
from app.tools.pipeline_tools import get_pipeline_summary
from app.tools.revenue_tools import get_revenue_realization_summary
from app.tools.operations_tools import get_work_order_health, get_cross_board_conversion, get_data_debt_report
from app.tools.executive_tools import get_executive_brief

TOOLS = [
    {
        "name": "get_pipeline_summary",
        "description": "Calculates raw and weighted sales pipeline value, stage cohorts, and sector distributions from deals dataset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "Optional sector filter (e.g. 'Mining', 'Renewables')"},
                "owner": {"type": "string", "description": "Optional owner code filter"},
                "probability": {"type": "number", "description": "Minimum probability filter (0.0 to 1.0)"}
            }
        }
    },
    {
        "name": "get_revenue_realization_summary",
        "description": "Computes contracted value, billed revenue (excl GST), collected cash (incl GST), unbilled backlog, and realization rate %.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "Optional sector filter (e.g. 'Mining', 'Renewables')"}
            }
        }
    },
    {
        "name": "get_cross_board_conversion",
        "description": "Analyzes conversion from Won Deals to active Work Orders, identifying unlinked deals and conversion efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_work_order_health",
        "description": "Returns operational work order execution status breakdowns and flags delayed or stuck projects.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_data_debt_report",
        "description": "Generates audit checklist of data hygiene defects, missing critical fields, and unbilled completed orders.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_executive_brief",
        "description": "Synthesizes comprehensive high-level leadership KPIs, top operational wins, revenue risks, and period deltas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Reporting period (default: 'FY25-26')"}
            }
        }
    },
    {
        "name": "anonymize_text",
        "description": "Anonymizes sensitive customer, deal, and employee names into Blindfold session tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Plain text with potential PII entities"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "deanonymize_text",
        "description": "Restores Blindfold session tokens back to real entity names for authorized executive consumption.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Tokenized text containing session tokens"}
            },
            "required": ["text"]
        }
    }
]

def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    # Ensure DB is ready
    if not db.initialized:
        db.init_db()
        orchestrator.init_catalog()

    if tool_name == "get_pipeline_summary":
        return get_pipeline_summary(**arguments)
    elif tool_name == "get_revenue_realization_summary":
        return get_revenue_realization_summary(**arguments)
    elif tool_name == "get_cross_board_conversion":
        return get_cross_board_conversion()
    elif tool_name == "get_work_order_health":
        return get_work_order_health()
    elif tool_name == "get_data_debt_report":
        return get_data_debt_report()
    elif tool_name == "get_executive_brief":
        return get_executive_brief(**arguments)
    elif tool_name == "anonymize_text":
        return {"anonymized": blindfold.anonymize_text(arguments.get("text", ""))}
    elif tool_name == "deanonymize_text":
        return {"deanonymized": blindfold.deanonymize_text(arguments.get("text", ""))}
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

async def run_stdio_server():
    """Runs a standard JSON-RPC 2.0 stdio MCP server."""
    db.init_db()
    orchestrator.init_catalog()

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            req = json.loads(line.decode("utf-8"))
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                result_content = handle_tool_call(name, args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result_content, indent=2)}]
                    }
                }
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(run_stdio_server())
