"""
Dependencies, security, and RFC 7807 Problem Details for Blindfold BI API v1.
"""

import time
from typing import Dict, Optional
from collections import defaultdict
from fastapi import Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings


class ProblemException(HTTPException):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        code: str,
        instance: Optional[str] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.title = title
        self.code = code
        self.instance = instance


def problem_json_response(
    status_code: int,
    title: str,
    detail: str,
    code: str,
    instance: Optional[str] = None,
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
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


# In-memory IP rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.window = 60.0
        self.requests: Dict[str, list] = defaultdict(list)

    def check(self, ip: str) -> bool:
        now = time.time()
        # Clean older requests outside 60s window
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]
        if len(self.requests[ip]) >= self.limit:
            return False
        self.requests[ip].append(now)
        return True


rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def check_rate_limit(request: Request):
    """Enforces per-IP rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        raise ProblemException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            title="Rate Limit Exceeded",
            detail=f"Exceeded maximum request rate of {settings.RATE_LIMIT_PER_MINUTE} requests/min.",
            code="RATE_LIMIT_EXCEEDED",
            instance=request.url.path,
        )


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
) -> str:
    """Verifies X-API-Key header for protected programmatic endpoints."""
    expected_key = settings.API_KEY
    if not x_api_key or x_api_key.strip() != expected_key:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Missing or invalid X-API-Key header.",
            code="INVALID_API_KEY",
            instance=request.url.path if request else None,
        )
    return x_api_key
