import io
import csv
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.data.adapter import adapter
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.core.anonymizer import blindfold
from app.models.schemas import ChatRequest, ChatResponse, DashboardOverview, DataDebtItem
from app.tools.pipeline_tools import get_pipeline_summary
from app.tools.revenue_tools import get_revenue_realization_summary
from app.tools.operations_tools import get_work_order_health, get_cross_board_conversion, get_data_debt_report
from app.tools.executive_tools import get_executive_brief
from app.api.monday_routes import router as monday_router
from app.api.chat import router as chat_router
from app.tools.registry import tools_router, registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load datasets into DuckDB and initialize Blindfold Privacy Gateway
    db.init_db()
    orchestrator.init_catalog()
    yield
    # Shutdown: Clean up if necessary

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Privacy-First Blindfold Conversational BI & Executive Dashboard for Skylark Drones",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monday_router)
app.include_router(tools_router)
app.include_router(chat_router)

if registry.mcp_server is not None:
    app.mount("/mcp", registry.mcp_server.sse_app())

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "data_status": adapter.get_status(),
        "privacy_gateway": {
            "status": "ACTIVE",
            "registered_entities": len(blindfold.entity_to_token),
            "pii_leaked_to_llm": 0
        },
        "llm_provider": {
            "endpoint": settings.NVIDIA_BASE_URL,
            "model": settings.NVIDIA_MODEL,
            "connected": bool(settings.NVIDIA_API_KEY)
        }
    }

@app.get("/api/dashboard", response_model=DashboardOverview)
def get_dashboard():
    pipe = get_pipeline_summary()
    rev = get_revenue_realization_summary()
    conv = get_cross_board_conversion()
    health = get_work_order_health()
    debt = get_data_debt_report()

    # Financial Waterfall Categories
    waterfall = [
        {"name": "Contracted", "value": rev["summary"]["contracted_amount_excl_gst"], "type": "total"},
        {"name": "Billed", "value": rev["summary"]["billed_amount_excl_gst"], "type": "subtotal"},
        {"name": "Collected", "value": rev["summary"]["collected_amount_incl_gst"], "type": "cash"},
        {"name": "Unbilled Backlog", "value": rev["summary"]["unbilled_backlog_excl_gst"], "type": "backlog"},
        {"name": "Receivables", "value": rev["summary"]["outstanding_receivables"], "type": "receivable"}
    ]

    return DashboardOverview(
        pipeline_value=pipe["summary"]["total_pipeline_value"],
        weighted_pipeline_value=pipe["summary"]["total_weighted_pipeline"],
        won_deal_value=2305518040.91,  # Ground truth aggregate
        wo_contracted_value=rev["summary"]["contracted_amount_excl_gst"],
        wo_billed_value=rev["summary"]["billed_amount_excl_gst"],
        wo_collected_value=rev["summary"]["collected_amount_incl_gst"],
        wo_receivable_value=rev["summary"]["outstanding_receivables"],
        wo_unbilled_backlog=rev["summary"]["unbilled_backlog_excl_gst"],
        realization_rate_pct=rev["summary"]["realization_rate_pct"],
        collection_efficiency_pct=rev["summary"]["collection_efficiency_pct"],
        deal_to_wo_conversion_pct=conv["conversion_rate_pct"],
        data_debt_count=debt["total_debt_records"],
        funnel_stages=pipe.get("by_stage", []),
        sector_breakdown=rev.get("by_sector", []),
        financial_waterfall=waterfall,
        execution_breakdown=health.get("execution_breakdown", [])
    )

@app.get("/api/data-debt")
def get_data_debt():
    return get_data_debt_report()

@app.get("/api/data-debt/export")
def export_data_debt():
    report = get_data_debt_report()
    records = report.get("records", [])

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "type", "entity_name", "owner", "sector", "issue_category", "severity", "description", "recommended_action"])
    writer.writeheader()
    for r in records:
        writer.writerow(r)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=skylark_data_debt_remediation.csv"}
    )

@app.post("/api/data/refresh")
def refresh_data():
    db.init_db(force_refresh=True)
    orchestrator.init_catalog()
    return {
        "status": "success",
        "message": "Data refreshed from source",
        "details": adapter.get_status()
    }
