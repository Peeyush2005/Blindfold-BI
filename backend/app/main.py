"""
Blindfold BI - Skylark Drones
Production ASGI Application with Versioned v1 API, Health Probes, and MCP Server.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.data.adapter import adapter
from app.data.db import db
from app.core.orchestrator import orchestrator
from app.tools.registry import registry
from app.api.v1 import api_v1_router
from app.api.v1.deps import ProblemException, problem_json_response

# Structured logging setup
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger("blindfold.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DuckDB and Blindfold Privacy Gateway catalogs
    logger.info("Initializing DuckDB analytic tables...")
    db.init_db()
    logger.info("Initializing DataAdapter snapshot...")
    adapter.load_data()
    logger.info("Initializing Blindfold Privacy Gateway surrogate catalogs...")
    orchestrator.init_catalog()
    yield
    # Graceful shutdown
    logger.info("Shutting down Blindfold BI service...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Minimal, live, API-first Conversational Business Intelligence platform for Skylark Drones.\n\n"
        "Features:\n"
        "- Zero LLM access to raw commercial datasets\n"
        "- Numbers-by-reference fact grounding with strict verification\n"
        "- Real-time 8-stage pipeline event streaming over SSE\n"
        "- Model Context Protocol (MCP) tool server\n"
        "- Strict read-only governance over monday.com boards"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS allow-list configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Type"],
)


# Request ID and Structured Logging Middleware
@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    t0 = time.time()

    response: Response = await call_next(request)

    latency_ms = round((time.time() - t0) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    # Structured access log without logging raw payloads or row data
    logger.info(
        f'{{"request_id": "{request_id}", "method": "{request.method}", "path": "{request.url.path}", '
        f'"status": {response.status_code}, "latency_ms": {latency_ms}}}'
    )
    return response


# RFC 7807 Problem Exception Handler
@app.exception_handler(ProblemException)
async def problem_exception_handler(request: Request, exc: ProblemException):
    return problem_json_response(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        code=exc.code,
        instance=request.url.path,
    )


# Mount Versioned v1 API
app.include_router(api_v1_router)

# Mount MCP Server if available
if registry.mcp_server is not None:
    try:
        app.mount("/mcp", registry.mcp_server.sse_app())
        logger.info("Mounted MCP server at /mcp")
    except Exception as e:
        logger.warning(f"Failed to mount FastMCP SSE app: {e}")


# -----------------------------------------------------------------------------
# Cloud-Native Health & Readiness Probes
# -----------------------------------------------------------------------------

@app.get(
    "/healthz",
    tags=["Probes"],
    summary="Liveness Probe",
    description="Kubernetes/container liveness probe confirming the HTTP server is responsive.",
)
async def healthz():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
    }


@app.get(
    "/readyz",
    tags=["Probes"],
    summary="Readiness Probe",
    description="Kubernetes/container readiness probe confirming DuckDB, snapshot data, metric contracts, and LLM are ready to serve traffic.",
)
async def readyz():
    checks = {
        "duckdb": db.store.con is not None and db.store.initialized,
        "data_snapshot": (adapter.deals_df is not None and adapter.wo_df is not None),
        "metric_contracts": bool(orchestrator.contract_manager.metrics),
        "llm_configuration": bool(settings.NVIDIA_API_KEY) or (settings.LLM_MODE == "off"),
    }

    is_ready = all(checks.values())
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    content = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "as_of_date": settings.AS_OF_DATE,
        "source": "monday.com",
    }

    if not is_ready:
        return JSONResponse(
            status_code=status_code,
            content={
                "type": "https://api.skylark.ai/errors/NOT_READY",
                "title": "Service Not Ready",
                "status": status_code,
                "detail": "One or more readiness dependencies are unavailable.",
                "code": "NOT_READY",
                "checks": checks,
            },
        )

    return JSONResponse(status_code=status_code, content=content)


# Backwards compatibility /health endpoint
@app.get("/health", include_in_schema=False)
async def legacy_health():
    return await healthz()
