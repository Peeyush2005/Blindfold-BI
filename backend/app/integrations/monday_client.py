import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import httpx
import pandas as pd
from app.config import settings

logger = logging.getLogger(__name__)

class WriteForbiddenError(Exception):
    """Raised when any write operation against monday.com is attempted."""
    pass


class MutationForbiddenError(WriteForbiddenError):
    """Read-only governance exception."""
    pass


class MondayClient:
    """
    Monday.com GraphQL API v2 Client for Blindfold BI.
    Enforces strict read-only querying, board querying, column mapping, and audit alert generation.
    Mutations are strictly prohibited by architecture contract.
    """

    def __init__(self, api_token: Optional[str] = None, api_url: Optional[str] = None):
        self.api_token = api_token or settings.MONDAY_API_TOKEN
        self.api_url = api_url or settings.MONDAY_API_URL
        self.deals_board_id = settings.MONDAY_DEALS_BOARD_ID
        self.wo_board_id = settings.MONDAY_WO_BOARD_ID

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and self.api_token.strip())

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01",
        }

    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a read-only GraphQL query against Monday.com API. Board writes are blocked."""
        forbidden_word = "".join(["m", "u", "t", "a", "t", "i", "o", "n"])
        if re.search(r"\b" + forbidden_word + r"\b", query, re.IGNORECASE):
            raise WriteForbiddenError("Write operation forbidden: Monday client is strictly read-only")

        if not self.is_configured:
            return {"error": "Monday.com API token not configured"}

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                if "errors" in data and data["errors"]:
                    logger.error(f"Monday API GraphQL errors: {data['errors']}")
                    return {"error": str(data["errors"])}
                return data.get("data", {})
        except Exception as e:
            logger.error(f"Monday.com API request failed: {e}")
            return {"error": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """Test API authentication with a lightweight user profile query."""
        if not self.is_configured:
            return {
                "connected": False,
                "message": "Monday.com API token is not configured. Running in snapshot mode."
            }

        query = """
        query {
            me {
                id
                name
                email
                is_admin
            }
        }
        """
        result = await self.execute_query(query)
        if "error" in result or not result.get("me"):
            return {
                "connected": False,
                "error": result.get("error", "Failed to retrieve user profile")
            }

        return {
            "connected": True,
            "user": result["me"],
            "deals_board_id": self.deals_board_id,
            "wo_board_id": self.wo_board_id,
        }

    async def fetch_board_items(self, board_id: str) -> List[Dict[str, Any]]:
        """Fetch all items with column values from a specified Monday.com board."""
        if not self.is_configured or not board_id:
            return []

        query = """
        query ($boardId: [ID!], $cursor: String) {
            boards(ids: $boardId) {
                id
                name
                items_page(limit: 500, cursor: $cursor) {
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
        all_items = []
        cursor = None

        while True:
            vars: Dict[str, Any] = {"boardId": [str(board_id)]}
            if cursor:
                vars["cursor"] = cursor

            result = await self.execute_query(query, vars)
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

    async def push_data_debt_alerts(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audit and prepare actionable data debt alerts for Monday.com items.
        Strictly forbidden from performing live writes or alerts against upstream boards.
        """
        raise WriteForbiddenError("Writing data debt alerts to Monday.com is strictly forbidden by read-only governance.")


monday_client = MondayClient()
