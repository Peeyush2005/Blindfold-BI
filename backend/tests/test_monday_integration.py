import subprocess
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.integrations.monday_client import MondayClient, WriteForbiddenError, MutationForbiddenError

client = TestClient(app)


def test_monday_meta_source_endpoint():
    """Validates GET /api/v1/meta/source returns connection status, row counts, and display badge with no secrets."""
    response = client.get("/api/v1/meta/source")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["source"] == "monday.com"
    assert data["as_of_date"] == "15 Jan 2026"
    assert data["deals_count"] == 332
    assert data["work_orders_count"] == 176
    assert "monday.com · synced" in data["display_badge"]
    assert "as of 15 Jan 2026" in data["display_badge"]
    # Ensure no tokens or secrets are exposed
    assert "token" not in data
    assert "secret" not in data
    assert "key" not in data


def test_monday_data_refresh_endpoint_security():
    """POST /api/v1/data/refresh must be protected with X-API-Key."""
    # Without key -> 401
    res_unauth = client.post("/api/v1/data/refresh")
    assert res_unauth.status_code == 401

    # With valid key -> 200
    res_auth = client.post("/api/v1/data/refresh", headers={"X-API-Key": settings.API_KEY})
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["status"] == "success"
    assert data["details"]["deals_count"] == 332
    assert data["details"]["work_orders_count"] == 176


def test_removed_write_and_config_routes_return_404():
    """Asserts that all removed write and configuration routes return 404."""
    assert client.post("/api/monday/configure", json={}).status_code == 404
    assert client.post("/api/monday/push-debt-alerts").status_code == 404
    assert client.post("/api/monday/webhook", json={}).status_code == 404
    assert client.get("/api/dashboard").status_code == 404
    assert client.get("/api/data-debt").status_code == 404
    assert client.post("/api/data/refresh").status_code == 404


def test_monday_client_headers():
    m_client = MondayClient(api_token="test_token_12345")
    headers = m_client._get_headers()
    assert headers["Authorization"] == "test_token_12345"
    assert headers["API-Version"] == "2024-01"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_strict_read_only_mutation_forbidden():
    """Verifies that any write operation on MondayClient raises WriteForbiddenError."""
    m_client = MondayClient(api_token="test_token_12345")
    with pytest.raises((WriteForbiddenError, MutationForbiddenError)):
        await m_client.push_data_debt_alerts([{"id": "123"}])


def test_zero_mutation_in_backend_code():
    """Verifies grep -rn 'mutation' backend/app returns 0 occurrences."""
    result = subprocess.run(
        ["grep", "-rn", "mutation", "backend/app"],
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", f"Found prohibited 'mutation' keyword in backend/app: {result.stdout}"
