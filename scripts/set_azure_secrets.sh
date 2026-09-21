#!/usr/bin/env bash
# =============================================================================
# Blindfold BI - Azure Container Apps Secret Configuration (Section 8a)
# Prompts silently for sensitive credentials and securely updates Container App secrets.
#
# Usage:
#   ./scripts/set_azure_secrets.sh [app_name] [resource_group]
# =============================================================================

set -euo pipefail

APP_NAME="${1:-skylark-bi-api}"
RESOURCE_GROUP="${2:-rg-blindfold-bi-central}"

echo "================================================================="
echo " Blindfold BI: Azure Container App Secret Provisioning"
echo " Target App:           $APP_NAME"
echo " Target Resource Group: $RESOURCE_GROUP"
echo "================================================================="
echo ""

# Check azure cli login
if ! az account show >/dev/null 2>&1; then
  echo "Error: Azure CLI is not logged in. Please run 'az login' first."
  exit 1
fi

echo -n "Enter NVIDIA API Key (e.g. nvapi-...): "
read -rs NVIDIA_KEY
echo ""

if [[ -z "$NVIDIA_KEY" ]]; then
  echo "Error: NVIDIA API Key cannot be empty."
  exit 1
fi

echo -n "Enter monday.com API Token: "
read -rs MONDAY_TOKEN
echo ""

if [[ -z "$MONDAY_TOKEN" ]]; then
  echo "Error: monday.com API Token cannot be empty."
  exit 1
fi

echo -n "Enter Admin Token for API Key Management (press enter to auto-generate random 48-char secret): "
read -rs ADMIN_TOKEN
echo ""

if [[ -z "$ADMIN_TOKEN" ]]; then
  ADMIN_TOKEN=$(openssl rand -hex 24)
  echo "Generated Admin Token: $ADMIN_TOKEN"
  echo "IMPORTANT: Save this token to manage API keys via scripts/keys.sh"
fi

echo -n "Enter API Key Pepper (press enter to auto-generate random 32-byte secret): "
read -rs PEPPER
echo ""

if [[ -z "$PEPPER" ]]; then
  PEPPER=$(openssl rand -hex 32)
  echo "Generated API Key Pepper."
fi

echo ""
echo "Setting secrets on Azure Container App '$APP_NAME'..."

az containerapp secret set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --secrets \
    nvidia-api-key="$NVIDIA_KEY" \
    monday-api-token="$MONDAY_TOKEN" \
    admin-token="$ADMIN_TOKEN" \
    api-key-pepper="$PEPPER"

echo "Secrets stored. Updating environment variables to reference secrets..."

az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars \
    NVIDIA_API_KEY="secretref:nvidia-api-key" \
    MONDAY_API_TOKEN="secretref:monday-api-token" \
    ADMIN_TOKEN="secretref:admin-token" \
    API_KEY_PEPPER="secretref:api-key-pepper"

echo ""
echo "Successfully provisioned secrets and triggered new revision for '$APP_NAME'."
