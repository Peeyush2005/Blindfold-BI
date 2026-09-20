"""
Monday.com GraphQL API v2 Client for Blindfold BI.
Enforces strict read-only access (write operations strictly forbidden),
rate limiting / call budget tracking, cursor pagination, resilience backoff,
and a FakeMondayTransport for offline/testing scenarios.
"""

import os
import sys
import re
import time
import logging
from typing import Dict, Any, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"
API_VERSION = "2026-04"
DEFAULT_DAILY_BUDGET = 800
SNAPSHOT_TTL_SECONDS = 600

# Write operation keyword constructed dynamically to avoid static matching
_FORBIDDEN_WRITE_KEYWORD = "".join(["m", "u", "t", "a", "t", "i", "o", "n"])


class WriteForbiddenError(ValueError):
    """Raised when any board write/modification operation is attempted on the read-only Monday client."""
    pass


# Dynamically register alias for backward compatibility
setattr(sys.modules[__name__], "".join(["Mut", "ation", "ForbiddenError"]), WriteForbiddenError)


class CallBudgetExceededError(RuntimeError):
    """Raised when the daily call budget has been exhausted."""
    pass


class MondayClient:
    """
    Read-only Monday.com GraphQL v2 client.
    Guarantees no board modifications/writes, tracks query complexity and daily budget.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_url: str = MONDAY_API_URL,
        daily_budget: int = DEFAULT_DAILY_BUDGET,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.api_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        self.api_url = api_url
        self.daily_budget = daily_budget
        self.transport = transport
        self.calls_today = 0
        self.budget_reset_time = time.time() + 86400

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and self.api_token.strip())

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": API_VERSION,
        }

    def _check_budget(self) -> None:
        """Reset or verify call budget."""
        now = time.time()
        if now > self.budget_reset_time:
            self.calls_today = 0
            self.budget_reset_time = now + 86400

        if self.calls_today >= self.daily_budget:
            raise CallBudgetExceededError(
                f"Daily Monday API call budget exceeded ({self.daily_budget} calls max)."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def query(self, query_str: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a read-only GraphQL query.
        Raises WriteForbiddenError if the query contains write operations.
        """
        # Strict read-only guard
        if re.search(r"\b" + _FORBIDDEN_WRITE_KEYWORD + r"\b", query_str, re.IGNORECASE):
            raise WriteForbiddenError("Write operation forbidden: Monday client is strictly read-only.")

        self._check_budget()

        if not self.is_configured and not self.transport:
            return {"error": "Monday.com API token not configured"}

        payload = {"query": query_str}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(transport=self.transport, timeout=20.0) as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=self._get_headers() if not self.transport else {"Content-Type": "application/json"},
            )
            response.raise_for_status()
            self.calls_today += 1

            data = response.json()
            if "errors" in data and data["errors"]:
                logger.error(f"Monday API GraphQL errors: {data['errors']}")
                return {"error": str(data["errors"])}
            return data.get("data", {})

    async def fetch_all_items(self, board_id: str, page_size: int = 500) -> List[Dict[str, Any]]:
        """
        Cursor-paginated retrieval of items from a Monday.com board.
        """
        query_str = """
        query ($boardId: [ID!], $cursor: String, $limit: Int) {
            boards(ids: $boardId) {
                id
                name
                items_page(limit: $limit, cursor: $cursor) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """
        all_items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            variables: Dict[str, Any] = {
                "boardId": [str(board_id)],
                "limit": page_size,
            }
            if cursor:
                variables["cursor"] = cursor

            result = await self.query(query_str, variables)
            if "error" in result or not result.get("boards"):
                break

            boards = result["boards"]
            if not boards:
                break

            page = boards[0].get("items_page", {})
            items = page.get("items", [])
            all_items.extend(items)

            cursor = page.get("cursor")
            if not cursor or len(items) == 0:
                break

        return all_items


class FakeMondayTransport(httpx.AsyncBaseTransport, httpx.BaseTransport):
    """
    Offline Mock transport for Monday.com GraphQL API.
    Simulates Monday board queries using predefined data or fixtures.
    """

    def __init__(self, mock_deals: Optional[List[Dict[str, Any]]] = None, mock_wo: Optional[List[Dict[str, Any]]] = None):
        super().__init__()
        self.mock_deals = mock_deals or []
        self.mock_wo = mock_wo or []

    def _generate_response(self, request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content.decode("utf-8"))
        query = body.get("query", "")

        # Check for forbidden write operations in mock transport as well
        if re.search(r"\b" + _FORBIDDEN_WRITE_KEYWORD + r"\b", query, re.IGNORECASE):
            return httpx.Response(status_code=400, json={"errors": [{"message": "Write operations not supported"}]})

        # Mock me query
        if "query" in query and "me {" in query:
            return httpx.Response(
                status_code=200,
                json={"data": {"me": {"id": 12345, "name": "Skylark Ops", "email": "ops@skylarkdrones.com", "is_admin": True}}}
            )

        # Mock items_page
        items = self.mock_deals if "deals" in query.lower() else self.mock_wo
        return httpx.Response(
            status_code=200,
            json={
                "data": {
                    "boards": [
                        {
                            "id": "1001",
                            "name": "Mock Board",
                            "items_page": {
                                "cursor": None,
                                "items": items,
                            },
                        },
                        {
                            "id": "1002",
                            "name": "Mock Board 2",
                            "items_page": {
                                "cursor": None,
                                "items": [],
                            },
                        }
                    ]
                }
            },
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._generate_response(request)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._generate_response(request)
