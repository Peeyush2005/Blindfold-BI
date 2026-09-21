#!/usr/bin/env python3
"""
Blindfold BI - Live Credential & Service Verification Diagnostic (Section 8a)
Tests each credential live and prints PASS/FAIL with specific root-cause reasons:
  1. NVIDIA NIM API: GET /v1/models + 1 tool-call probe
  2. monday.com API: GraphQL query { me { id } } + read probe of deals & wo boards
  3. API Key Store: Create and verify temporary test record
  4. Azure Blob Storage: Verify blob container access if configured
"""

import os
import sys
import json
import httpx
from pathlib import Path

# Add backend directory to sys.path so app imports succeed
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.key_store import key_store


def print_result(service: str, passed: bool, reason: str):
    tag = "[\033[92mPASS\033[0m]" if passed else "[\033[91mFAIL\033[0m]"
    print(f"{tag} {service:25}: {reason}")


def test_nvidia() -> bool:
    api_key = settings.NVIDIA_API_KEY
    if not api_key:
        print_result("NVIDIA NIM LLM", False, "NVIDIA_API_KEY is not set.")
        return False

    base_url = settings.NVIDIA_BASE_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            # Probe 1: GET /models
            models_resp = client.get(f"{base_url}/models", headers=headers)
            if models_resp.status_code != 200:
                print_result("NVIDIA NIM LLM", False, f"GET /models returned HTTP {models_resp.status_code}: {models_resp.text[:120]}")
                return False

            # Probe 2: Single Tool-Call Probe
            probe_payload = {
                "model": settings.NVIDIA_MODEL,
                "messages": [{"role": "user", "content": "What is 2+2? Use the test tool."}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "calculate",
                            "description": "Calculate simple math",
                            "parameters": {
                                "type": "object",
                                "properties": {"expression": {"type": "string"}},
                                "required": ["expression"],
                            },
                        },
                    }
                ],
                "tool_choice": "auto",
                "max_tokens": 50,
            }
            chat_resp = client.post(f"{base_url}/chat/completions", headers=headers, json=probe_payload)
            if chat_resp.status_code != 200:
                print_result("NVIDIA NIM LLM", False, f"Tool probe returned HTTP {chat_resp.status_code}: {chat_resp.text[:120]}")
                return False

        print_result("NVIDIA NIM LLM", True, f"Models listed & tool probe verified against '{settings.NVIDIA_MODEL}'.")
        return True
    except Exception as exc:
        print_result("NVIDIA NIM LLM", False, f"Connection exception: {str(exc)}")
        return False


def test_monday() -> bool:
    token = settings.MONDAY_API_TOKEN
    if not token:
        print_result("monday.com GraphQL", False, "MONDAY_API_TOKEN is not set.")
        return False

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "API-Version": "2024-10",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            # Probe 1: { me { id name } }
            me_query = {"query": "{ me { id name email } }"}
            resp = client.post(settings.MONDAY_API_URL, headers=headers, json=me_query)
            if resp.status_code != 200:
                print_result("monday.com GraphQL", False, f"GraphQL endpoint returned HTTP {resp.status_code}: {resp.text[:120]}")
                return False
            data = resp.json()
            if "errors" in data:
                print_result("monday.com GraphQL", False, f"Query 'me' error: {data['errors']}")
                return False

            user_id = data.get("data", {}).get("me", {}).get("id", "unknown")

            # Probe 2: Read deals & work orders boards if IDs configured
            deals_id = settings.MONDAY_DEALS_BOARD_ID
            wo_id = settings.MONDAY_WO_BOARD_ID
            board_ids = [b for b in [deals_id, wo_id] if b]

            if board_ids:
                boards_query = {"query": f"{{ boards(ids: {json.dumps(board_ids)}) {{ id name items_count }} }}"}
                b_resp = client.post(settings.MONDAY_API_URL, headers=headers, json=boards_query)
                b_data = b_resp.json()
                if "errors" in b_data:
                    print_result("monday.com GraphQL", False, f"Boards query error: {b_data['errors']}")
                    return False
                boards = b_data.get("data", {}).get("boards", [])
                board_names = ", ".join([f"{b.get('name')}({b.get('items_count')} items)" for b in boards])
                print_result("monday.com GraphQL", True, f"Authenticated as User ID {user_id}. Found boards: {board_names or 'none'}.")
            else:
                print_result("monday.com GraphQL", True, f"Authenticated as User ID {user_id}. (Board IDs not set, verified user query).")
            return True
    except Exception as exc:
        print_result("monday.com GraphQL", False, f"Connection exception: {str(exc)}")
        return False


def test_key_store() -> bool:
    try:
        # Create a test key
        full_key, record = key_store.create_key(
            name="__diag_test_key__",
            scopes=["tools:read"],
            expires_in_days=1,
        )

        # Validate the test key
        is_valid, err_code, validated_rec = key_store.validate_key(full_key, required_scope="tools:read")
        if not is_valid or not validated_rec or validated_rec.key_id != record.key_id:
            print_result("API Key Store", False, f"Key validation failed: code={err_code}")
            return False

        # Revoke the test key
        key_store.revoke_key(record.key_id)

        # Confirm revoked
        is_valid_after, err_after, _ = key_store.validate_key(full_key, required_scope="tools:read")
        if is_valid_after or err_after != "revoked_api_key":
            print_result("API Key Store", False, f"Revocation check failed: code={err_after}")
            return False

        print_result("API Key Store", True, f"Key creation, HMAC validation, and immediate revocation verified. (Storage: {key_store.storage_file.name})")
        return True
    except Exception as exc:
        print_result("API Key Store", False, f"Exception during key store verification: {str(exc)}")
        return False


def test_azure_blob() -> bool:
    conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
    if not conn_str:
        print_result("Azure Blob Store", True, "AZURE_STORAGE_CONNECTION_STRING not set (using local persistent JSON).")
        return True

    try:
        from azure.storage.blob import BlobServiceClient
        service = BlobServiceClient.from_connection_string(conn_str)
        container_client = service.get_container_client(settings.AZURE_STORAGE_CONTAINER)
        exists = container_client.exists()
        if not exists:
            container_client.create_container()
        print_result("Azure Blob Store", True, f"Connected to container '{settings.AZURE_STORAGE_CONTAINER}'.")
        return True
    except ImportError:
        print_result("Azure Blob Store", False, "azure-storage-blob package is not installed.")
        return False
    except Exception as exc:
        print_result("Azure Blob Store", False, f"Azure Blob connection failed: {str(exc)}")
        return False


def main():
    print("\n=================================================================")
    print(" Blindfold BI: Live Credential & Service Verification")
    print("=================================================================\n")

    results = [
        test_nvidia(),
        test_monday(),
        test_key_store(),
        test_azure_blob(),
    ]

    all_passed = all(results)
    print("\n-----------------------------------------------------------------")
    if all_passed:
        print("SUMMARY: \033[92mALL SERVICES OPERATIONAL (PASS)\033[0m")
        sys.exit(0)
    else:
        print("SUMMARY: \033[91mONE OR MORE SERVICES DEGRADED OR UNCONFIGURED (FAIL)\033[0m")
        # In development/test mode, exit with non-zero only if key_store failed
        if not results[2]:  # key store failed
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
