#!/usr/bin/env python3
"""
List all boards accessible by MONDAY_API_TOKEN in .env
"""
import os
import sys
import json
import httpx
from pathlib import Path

# Add backend directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings

def main():
    token = settings.MONDAY_API_TOKEN
    if not token:
        print("ERROR: MONDAY_API_TOKEN is empty in settings/.env")
        sys.exit(1)

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "API-Version": "2024-10",
    }

    # 1. Who am I?
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(settings.MONDAY_API_URL, headers=headers, json={"query": "{ me { id name email } }"})
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)
        me_data = resp.json()
        if "errors" in me_data:
            print(f"Errors in me query: {me_data['errors']}")
            sys.exit(1)
        me = me_data.get("data", {}).get("me", {})
        print(f"Authenticated as: {me.get('name')} ({me.get('email')}, ID: {me.get('id')})")

        # 2. List boards
        boards_query = """
        query {
            boards(limit: 50) {
                id
                name
                state
                board_kind
                items_count
                workspace { id name }
                columns { id title type }
            }
        }
        """
        b_resp = client.post(settings.MONDAY_API_URL, headers=headers, json={"query": boards_query})
        if b_resp.status_code != 200:
            print(f"HTTP {b_resp.status_code}: {b_resp.text}")
            sys.exit(1)
        b_data = b_resp.json()
        if "errors" in b_data:
            print(f"Errors in boards query: {b_data['errors']}")
            sys.exit(1)

        boards = b_data.get("data", {}).get("boards", [])
        print(f"\nFound {len(boards)} boards:")
        for b in boards:
            ws = b.get("workspace") or {}
            ws_name = ws.get("name", "Default")
            print(f"- Board ID: {b['id']}")
            print(f"  Name: {b['name']}")
            print(f"  Workspace: {ws_name}")
            print(f"  Items: {b.get('items_count')}")
            col_titles = [c['title'] for c in b.get('columns', [])]
            print(f"  Columns ({len(col_titles)}): {', '.join(col_titles[:8])}...")

if __name__ == "__main__":
    main()
