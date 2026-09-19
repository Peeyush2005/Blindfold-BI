import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.integrations.monday_client import MondayClient

client = TestClient(app)

def test_monday_status_endpoint():
    response = client.get("/api/monday/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "api_configured" in data
    assert "boards" in data
    assert "webhook_url" in data
    assert "/api/monday/webhook" in data["webhook_url"]

def test_monday_webhook_challenge():
    test_challenge = "secret-monday-challenge-code-9988"
    response = client.post("/api/monday/webhook", json={"challenge": test_challenge})
    assert response.status_code == 200
    assert response.json() == {"challenge": test_challenge}

def test_monday_webhook_event_trigger():
    payload = {
        "event": {
            "type": "change_column_value",
            "boardId": 987654321,
            "itemId": 123456789,
            "columnId": "status"
        }
    }
    response = client.post("/api/monday/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["event_type"] == "change_column_value"
    assert data["processed"] is True

def test_monday_push_debt_alerts():
    response = client.post("/api/monday/push-debt-alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary" in data
    assert data["summary"]["total_anomalies"] == 31
    assert data["summary"]["alerts_processed"] == 31

def test_monday_manual_sync():
    response = client.post("/api/monday/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["deals_synced"] == 342
    assert data["work_orders_synced"] == 175

def test_monday_client_headers():
    m_client = MondayClient(api_token="test_token_12345")
    headers = m_client._get_headers()
    assert headers["Authorization"] == "test_token_12345"
    assert headers["API-Version"] == "2024-01"
    assert headers["Content-Type"] == "application/json"
