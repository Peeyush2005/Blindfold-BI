"""
Typed analytical tool catalog and programmatic invocation endpoints for Blindfold BI API v1.
Secured with X-API-Key and per-IP rate limits.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel, Field

from app.tools.registry import registry, ToolMetadata, ToolCallRequest
from app.tools.chips import get_starter_chips
from app.contracts import ToolResult, ChipCandidate
from app.api.v1.deps import require_api_key, check_rate_limit, ProblemException

router = APIRouter(prefix="/tools", tags=["Tools Catalog & Execution v1"])


@router.get(
    "",
    response_model=List[ToolMetadata],
    summary="List Analytical Tools Catalog",
    description="Retrieve the complete registry of 14 deterministic DuckDB tools with typed JSON schemas.",
    dependencies=[Depends(check_rate_limit), Depends(require_api_key("tools:read"))],
    responses={
        200: {"description": "Array of tool metadata with JSON schemas."},
        401: {"description": "Unauthorized - invalid or missing X-API-Key."},
        403: {"description": "Forbidden - insufficient scope."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def list_tools():
    return registry.list_tools()


@router.get(
    "/starter-chips",
    response_model=List[ChipCandidate],
    summary="Get Starter Suggestion Chips",
    description="Retrieve canonical empty-state starter suggestion chips for the browser UI.",
    dependencies=[Depends(check_rate_limit)],
    responses={
        200: {"description": "List of starter chips."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def get_starter_chips_endpoint():
    return get_starter_chips()


@router.post("/starter-chips", include_in_schema=False)
async def starter_chips_post_not_allowed():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Method Not Allowed",
        headers={"Allow": "GET, HEAD, OPTIONS"},
    )


@router.get(
    "/{name}/schema",
    summary="Get Tool Schema by Name",
    description="Retrieve parameter schema and description for a specific tool.",
    dependencies=[Depends(check_rate_limit), Depends(require_api_key("tools:read"))],
    responses={
        200: {"description": "Tool parameter schema."},
        401: {"description": "Unauthorized - invalid or missing X-API-Key."},
        403: {"description": "Forbidden - insufficient scope."},
        404: {"description": "Tool not found."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def get_tool_schema_endpoint(name: str, request: Request):
    tool_def = registry.get_tool(name)
    if not tool_def:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tool Not Found",
            detail=f"Tool '{name}' is not registered in the catalog.",
            code="TOOL_NOT_FOUND",
            instance=request.url.path,
        )
    return {
        "name": tool_def.name,
        "domain": tool_def.domain,
        "description": tool_def.description,
        "parameters": tool_def.parameters_schema,
    }


@router.post(
    "/{name}",
    response_model=Dict[str, Any],
    summary="Execute Analytical Tool by Name",
    description="Programmatically execute a deterministic analytical tool with typed parameters.",
    dependencies=[Depends(check_rate_limit), Depends(require_api_key("tools:read"))],
    responses={
        200: {"description": "Structured ToolResult output."},
        401: {"description": "Unauthorized - invalid or missing X-API-Key."},
        403: {"description": "Forbidden - insufficient scope."},
        404: {"description": "Tool not found in catalog."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def execute_tool_endpoint(name: str, payload: ToolCallRequest, request: Request):
    if name not in registry._tools:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Tool Not Found",
            detail=f"Tool '{name}' is not registered in the catalog.",
            code="TOOL_NOT_FOUND",
            instance=request.url.path,
        )

    try:
        result = registry.execute_tool(name, payload.args)
        return result.model_dump()
    except Exception as e:
        raise ProblemException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Tool Execution Error",
            detail=f"Failed to execute tool '{name}': {str(e)}",
            code="TOOL_EXECUTION_ERROR",
            instance=request.url.path,
        )
