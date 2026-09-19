import logging
import json
from typing import Dict, Any, List, Optional, Tuple
import httpx
import pandas as pd
from app.config import settings

logger = logging.getLogger(__name__)

class MondayClient:
    """
    Monday.com GraphQL API v2 Client for Blindfold BI.
    Handles board querying, column mapping, webhook events, and two-way status updates.
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
        """Execute a GraphQL query against Monday.com API."""
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

    async def post_item_update(self, item_id: str, body: str) -> bool:
        """Create an update (comment / alert) on a Monday.com item."""
        if not self.is_configured or not item_id:
            return False

        mutation = """
        mutation ($itemId: ID!, $body: String!) {
            create_update(item_id: $itemId, body: $body) {
                id
            }
        }
        """
        result = await self.execute_query(mutation, {"itemId": str(item_id), "body": body})
        return "error" not in result and bool(result.get("create_update", {}).get("id"))

    async def push_data_debt_alerts(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Push actionable data debt alerts to Monday.com items.
        If live item ID is present, posts an update; otherwise simulates in test mode.
        """
        success_count = 0
        skipped_count = 0
        details = []

        for item in anomalies:
            severity = str(item.get("severity", "Medium")).upper()
            if severity not in ["HIGH", "MEDIUM"]:
                skipped_count += 1
                continue

            entity_id = item.get("id", "")
            entity_name = item.get("entity_name", "Unknown")
            issue = item.get("issue_category", "Data Anomaly")
            desc = item.get("description", "")
            action = item.get("recommended_action", "")

            body = (
                f"🚨 **[Blindfold BI Audit Alert - {severity} Severity]**\n\n"
                f"**Issue**: {issue}\n"
                f"**Entity**: {entity_name} ({entity_id})\n"
                f"**Diagnosis**: {desc}\n\n"
                f"👉 **Action Required**: {action}\n"
                f"*Audited automatically by Skylark Blindfold BI Engine.*"
            )

            # If connected and Monday item ID exists (usually integer string in Monday)
            if self.is_configured and entity_id.isdigit():
                posted = await self.post_item_update(entity_id, body)
                if posted:
                    success_count += 1
                    details.append({"id": entity_id, "status": "posted"})
                else:
                    details.append({"id": entity_id, "status": "failed"})
            else:
                # Recorded in log / simulated
                success_count += 1
                details.append({"id": entity_id, "status": "simulated_success", "preview": body[:80]})

        return {
            "total_anomalies": len(anomalies),
            "alerts_processed": success_count,
            "skipped_low_severity": skipped_count,
            "details": details[:10]  # sample
        }


monday_client = MondayClient()
