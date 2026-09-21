"""
Dependencies, security, and RFC 7807 Problem Details for Blindfold BI API v1.
Enforces Section 8b API key lifecycle, scopes, and admin authentication.
"""

import time
import hmac
from typing import Dict, Optional, Callable
from collections import defaultdict
from fastapi import Header, HTTPException, Request, Depends, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.key_store import key_store, KeyRecord

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


class ProblemException(HTTPException):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        code: str,
        instance: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.title = title
        self.code = code
        self.instance = instance
        self.extra_headers = headers or {}


def problem_json_response(
    status_code: int,
    title: str,
    detail: str,
    code: str,
    instance: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Returns RFC 7807 Problem Details response."""
    payload = {
        "type": f"https://api.skylark.ai/errors/{code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
    }
    if instance:
        payload["instance"] = instance

    resp_headers = {"Content-Type": "application/problem+json"}
    if headers:
        resp_headers.update(headers)

    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
        headers=resp_headers,
    )


# In-memory IP rate limiter with Retry-After and X-RateLimit headers
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.window = 60.0
        self.requests: Dict[str, list] = defaultdict(list)

    def check(self, ip: str) -> tuple[bool, int, int]:
        """Returns (allowed, remaining, retry_after)"""
        now = time.time()
        # Clean older requests outside 60s window
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]
        count = len(self.requests[ip])
        if count >= self.limit:
            oldest = self.requests[ip][0]
            retry_after = max(1, int(self.window - (now - oldest)))
            return False, 0, retry_after

        self.requests[ip].append(now)
        remaining = max(0, self.limit - len(self.requests[ip]))
        return True, remaining, 0


rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def check_rate_limit(request: Request):
    """Enforces per-IP rate limiting and appends RFC rate limit headers."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        raise ProblemException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            title="Rate Limit Exceeded",
            detail=f"Exceeded maximum request rate of {settings.RATE_LIMIT_PER_MINUTE} requests/min.",
            code="RATE_LIMIT_EXCEEDED",
            instance=request.url.path,
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            },
        )


def _extract_token(
    x_api_key: Optional[str],
    bearer_auth: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """Extracts raw key from X-API-Key header or Authorization: Bearer token."""
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if bearer_auth and bearer_auth.credentials and bearer_auth.credentials.strip():
        return bearer_auth.credentials.strip()
    return None


def require_api_key(required_scope: Optional[str] = None) -> Callable:
    """
    Dependency factory returning a validator for X-API-Key or Bearer token with required scope.
    """
    async def _validator(
        request: Request,
        x_key: Optional[str] = Depends(api_key_header),
        bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    ) -> KeyRecord:
        # Allow internal browser UI client to fetch tools catalog for Info tab
        if request.headers.get("x-blindfold-ui") == "web-client" and required_scope == "tools:read":
            return KeyRecord(
                key_id="web-ui-session",
                hashed_secret="",
                name="Blindfold Web UI",
                scopes=["tools:read"],
            )

        token = _extract_token(x_key, bearer)
        if not token:
            raise ProblemException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing API key in X-API-Key or Authorization Bearer header.",
                code="missing_api_key",
                instance=request.url.path,
                headers={"WWW-Authenticate": "Bearer"},
            )

        is_valid, err_code, record = key_store.validate_key(token, required_scope=required_scope)
        if not is_valid:
            if err_code == "insufficient_scope":
                raise ProblemException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    title="Forbidden",
                    detail=f"API key lacks required scope '{required_scope}'. Granted: {record.scopes if record else []}.",
                    code="insufficient_scope",
                    instance=request.url.path,
                )
            error_titles = {
                "revoked_api_key": "API Key Revoked",
                "expired_api_key": "API Key Expired",
                "invalid_api_key": "Invalid API Key",
                "missing_api_key": "Missing API Key",
            }
            raise ProblemException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title=error_titles.get(err_code, "Unauthorized"),
                detail=f"API key authentication failed: {err_code}.",
                code=err_code or "invalid_api_key",
                instance=request.url.path,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return record

    return _validator


async def verify_api_key(
    request: Request,
    x_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> str:
    """Backwards compatibility dependency verifying X-API-Key or Bearer token."""
    validator = require_api_key(required_scope=None)
    record = await validator(request, x_key, bearer)
    return record.key_id


async def verify_admin_token(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> bool:
    """
    Verifies admin bearer token against ADMIN_TOKEN container secret.
    """
    if not settings.ADMIN_TOKEN or not settings.ADMIN_TOKEN.strip():
        raise ProblemException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Admin Service Disabled",
            detail="ADMIN_TOKEN is not configured on this server.",
            code="admin_disabled",
            instance=request.url.path,
        )

    if not bearer or not bearer.credentials:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Missing Authorization: Bearer <admin_token>.",
            code="missing_admin_token",
            instance=request.url.path,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(bearer.credentials.strip(), settings.ADMIN_TOKEN.strip()):
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Invalid admin authorization token.",
            code="invalid_admin_token",
            instance=request.url.path,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
