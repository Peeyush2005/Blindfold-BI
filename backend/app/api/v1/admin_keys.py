"""
Admin API Key Management Endpoints for Blindfold BI API v1.
Hidden from public OpenAPI schema, protected by Authorization: Bearer $ADMIN_TOKEN.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.core.key_store import key_store, VALID_SCOPES
from app.api.v1.deps import verify_admin_token, check_rate_limit, ProblemException

router = APIRouter(
    prefix="/admin/keys",
    tags=["Admin Key Management"],
    include_in_schema=False,
    dependencies=[Depends(check_rate_limit), Depends(verify_admin_token)],
)


class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="Human-readable label for the API key")
    scopes: List[str] = Field(..., description="List of granted scopes: chat:run, tools:read, data:refresh, mcp:use")
    expires_in_days: Optional[int] = Field(None, description="Expiration in days (null for indefinite)")


class RotateKeyRequest(BaseModel):
    expires_in_days: Optional[int] = Field(None, description="Expiration in days for the rotated key")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_key_endpoint(payload: CreateKeyRequest, request: Request):
    """Issues a new API key. The full secret is returned exactly once."""
    invalid = [s for s in payload.scopes if s not in VALID_SCOPES]
    if invalid:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid Scopes",
            detail=f"Scopes {invalid} are not permitted. Valid scopes: {sorted(list(VALID_SCOPES))}",
            code="invalid_scopes",
            instance=request.url.path,
        )

    try:
        full_key, record = key_store.create_key(
            name=payload.name,
            scopes=payload.scopes,
            expires_in_days=payload.expires_in_days,
        )
        return {
            "key": full_key,
            "key_id": record.key_id,
            "name": record.name,
            "scopes": record.scopes,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
        }
    except Exception as e:
        raise ProblemException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Key Creation Error",
            detail=str(e),
            code="key_creation_failed",
            instance=request.url.path,
        )


@router.get("")
async def list_keys_endpoint():
    """Lists metadata for all issued API keys. Secrets are never exposed."""
    return key_store.list_keys()


@router.delete("/{key_id}")
async def revoke_key_endpoint(key_id: str, request: Request):
    """Revokes an active API key immediately."""
    success = key_store.revoke_key(key_id)
    if not success:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Key Not Found",
            detail=f"API key '{key_id}' not found.",
            code="key_not_found",
            instance=request.url.path,
        )
    return {"status": "revoked", "key_id": key_id}


@router.post("/{key_id}/rotate")
async def rotate_key_endpoint(key_id: str, payload: RotateKeyRequest, request: Request):
    """Revokes the old key and issues a replacement with the same name and scopes."""
    rotated = key_store.rotate_key(key_id, expires_in_days=payload.expires_in_days)
    if not rotated:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Key Not Found",
            detail=f"Cannot rotate key '{key_id}': key not found.",
            code="key_not_found",
            instance=request.url.path,
        )
    full_key, new_rec = rotated
    return {
        "key": full_key,
        "key_id": new_rec.key_id,
        "name": new_rec.name,
        "scopes": new_rec.scopes,
        "created_at": new_rec.created_at,
        "expires_at": new_rec.expires_at,
        "rotated_from": key_id,
    }
