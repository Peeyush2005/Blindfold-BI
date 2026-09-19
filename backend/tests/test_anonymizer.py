import pytest
from app.core.anonymizer import BlindfoldGateway

def test_anonymizer_registration_and_replacement():
    gateway = BlindfoldGateway()
    deals = ["Project Alpha", "Project Beta", "Operation Sky"]
    clients = ["Acme Corp", "Skylark Enterprise"]
    owners = ["Alice Smith", "Bob Jones"]

    gateway.register_entities(deals, clients, owners)

    raw_text = "Alice Smith closed Project Alpha for Acme Corp."
    anonymized = gateway.anonymize_text(raw_text)

    # Assert PII is gone
    assert "Alice Smith" not in anonymized
    assert "Project Alpha" not in anonymized
    assert "Acme Corp" not in anonymized

    # Assert tokens are present
    assert "OWNER_REP_" in anonymized
    assert "PROJECT_DEAL_" in anonymized
    assert "CLIENT_ENT_" in anonymized

    # Assert round-trip de-anonymization
    restored = gateway.deanonymize_text(anonymized)
    assert restored == raw_text

def test_anonymize_nested_object():
    gateway = BlindfoldGateway()
    gateway.register_entities(["Deal 101"], ["Client Corp"], ["Owner Dave"])

    data = {
        "deal": "Deal 101",
        "client": "Client Corp",
        "metrics": {"owner": "Owner Dave", "value": 500000},
        "tags": ["Deal 101", "normal_tag"]
    }

    anonymized_data = gateway.anonymize_obj(data)

    assert anonymized_data["deal"] != "Deal 101"
    assert anonymized_data["client"] != "Client Corp"
    assert anonymized_data["metrics"]["owner"] != "Owner Dave"
    assert anonymized_data["metrics"]["value"] == 500000
    assert anonymized_data["tags"][1] == "normal_tag"
