import subprocess
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.data.monday_client import MondayClient, WriteForbiddenError, MutationForbiddenError

client = TestClient(app)


def test_monday_meta_source_endpoint_is_truthful(monkeypatch):
    """A token string alone must NOT be reported as a live monday.com connection."""
    # Token set but no board IDs and no reachable monday.com: the app must not claim to be connected.
    monkeypatch.setattr(settings, "MONDAY_API_TOKEN", "mock_monday_token")
    response = client.get("/api/v1/meta/source")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["source"] != "monday.com"
    assert "monday.com · synced" not in data["display_badge"]
    # Ensure no tokens or secrets are exposed
    assert "token" not in data
    assert "secret" not in data
    assert "key" not in data
    assert "mock_monday_token" not in response.text


def test_monday_data_refresh_endpoint_security():
    """POST /api/v1/data/refresh must be protected with X-API-Key and must report the real outcome."""
    res_unauth = client.post("/api/v1/data/refresh")
    assert res_unauth.status_code == 401

    res_auth = client.post("/api/v1/data/refresh", headers={"X-API-Key": settings.API_KEY})
    assert res_auth.status_code == 200
    data = res_auth.json()
    # In tests monday.com is not configured, so the honest answer is "failed" with the reason, never "success".
    assert data["status"] == "failed"
    assert "not configured" in data["message"] or "monday" in data["message"].lower()
    assert "stats" not in data["details"]


def test_removed_write_and_config_routes_return_404():
    """Asserts that all removed write and configuration routes return 404."""
    assert client.post("/api/monday/configure", json={}).status_code == 404
    assert client.post("/api/monday/push-debt-alerts").status_code == 404
    assert client.post("/api/monday/webhook", json={}).status_code == 404
    assert client.get("/api/dashboard").status_code == 404
    assert client.get("/api/data-debt").status_code == 404
    assert client.post("/api/data/refresh").status_code == 404


def test_monday_client_headers(monkeypatch):
    from app.data import monday_client as mc
    m_client = MondayClient(api_token="test_token_12345")
    monkeypatch.setattr(mc, "API_VERSION", "")
    headers = m_client._get_headers()
    assert headers["Authorization"] == "test_token_12345"
    assert "API-Version" not in headers  # unset = monday uses its current version
    assert headers["Content-Type"] == "application/json"
    monkeypatch.setattr(mc, "API_VERSION", "2026-04")
    assert m_client._get_headers()["API-Version"] == "2026-04"


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
