#!/usr/bin/env bash
# =============================================================================
# Blindfold BI - API Key Lifecycle CLI Wrapper (Section 8b)
# Usage:
#   scripts/keys.sh create <name> <scopes_comma_separated> [expires_in_days]
#   scripts/keys.sh list
#   scripts/keys.sh revoke <key_id>
#   scripts/keys.sh rotate <key_id> [expires_in_days]
# =============================================================================

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-dev-admin-token-super-secret-12345}"

cmd="${1:-}"

if [[ -z "$cmd" ]]; then
  echo "Usage: $0 {create|list|revoke|rotate} [args...]"
  exit 1
fi

case "$cmd" in
  create)
    name="${2:-Developer Key}"
    scopes_str="${3:-chat:run,tools:read,data:refresh,mcp:use}"
    expires_days="${4:-null}"

    # Convert comma-separated scopes to JSON array
    scopes_json=$(echo "$scopes_str" | awk -F',' '{printf "["; for(i=1;i<=NF;i++){printf "\"%s\"", $i; if(i<NF) printf ", "}; printf "]"}')

    payload="{\"name\": \"$name\", \"scopes\": $scopes_json"
    if [[ "$expires_days" != "null" ]]; then
      payload="$payload, \"expires_in_days\": $expires_days}"
    else
      payload="$payload}"
    fi

    echo "Creating API key for '$name' with scopes $scopes_json..."
    curl -s -X POST "$API_URL/api/v1/admin/keys" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload" | jq . || curl -s -X POST "$API_URL/api/v1/admin/keys" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload"
    ;;

  list)
    echo "Listing API keys from $API_URL..."
    curl -s -X GET "$API_URL/api/v1/admin/keys" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq . || curl -s -X GET "$API_URL/api/v1/admin/keys" \
      -H "Authorization: Bearer $ADMIN_TOKEN"
    ;;

  revoke)
    key_id="${2:-}"
    if [[ -z "$key_id" ]]; then
      echo "Usage: $0 revoke <key_id>"
      exit 1
    fi
    echo "Revoking key '$key_id'..."
    curl -s -X DELETE "$API_URL/api/v1/admin/keys/$key_id" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq . || curl -s -X DELETE "$API_URL/api/v1/admin/keys/$key_id" \
      -H "Authorization: Bearer $ADMIN_TOKEN"
    ;;

  rotate)
    key_id="${2:-}"
    expires_days="${3:-null}"
    if [[ -z "$key_id" ]]; then
      echo "Usage: $0 rotate <key_id> [expires_in_days]"
      exit 1
    fi
    payload="{}"
    if [[ "$expires_days" != "null" ]]; then
      payload="{\"expires_in_days\": $expires_days}"
    fi
    echo "Rotating key '$key_id'..."
    curl -s -X POST "$API_URL/api/v1/admin/keys/$key_id/rotate" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload" | jq . || curl -s -X POST "$API_URL/api/v1/admin/keys/$key_id/rotate" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload"
    ;;

  *)
    echo "Unknown command: $cmd"
    echo "Usage: $0 {create|list|revoke|rotate} [args...]"
    exit 1
    ;;
esac
