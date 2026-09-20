# Blindfold BI

Conversational Business Intelligence platform for Skylark Drones. Operates as an API-first analytical engine that executes deterministic DuckDB SQL queries over synchronized monday.com operational boards, protects proprietary entity data using session-scoped HMAC tokenization, and streams verified answers and generated BI visual blocks to a single-screen web interface.

---

## 1. Live Deployments & Endpoints

| Resource | URL | Description |
|---|---|---|
| **Production Web UI** | [https://mango-plant-08ea0340f.1.azurestaticapps.net](https://mango-plant-08ea0340f.1.azurestaticapps.net) | Single-screen conversational interface on Azure Static Web Apps |
| **Production API Gateway** | [https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io](https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io) | Autoscaling FastAPI async engine on Azure Container Apps |
| **Interactive API Docs** | [https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/docs](https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/docs) | Interactive Swagger UI documentation |
| **OpenAPI Specification** | [https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/openapi.json](https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/openapi.json) | Complete OpenAPI 3.1 contract |
| **Model Context Protocol (MCP)** | `https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/mcp` | JSON-RPC 2.0 endpoint for MCP-compatible clients |

---

## 2. System Architecture

The platform architecture completely separates data privacy, analytical computation, and natural language synthesis into distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT INTERFACE                                │
│  Single-Screen React 19 UI: Header Source Badge, Starter Chips, Input,      │
│  Live 8-Stage Run Panel (Auto-collapsing to summary), Generated BI Blocks   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / Server-Sent Events (SSE)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API & PIPELINE GATEWAY                            │
│  FastAPI Async Engine: /api/v1/chat, /api/v1/runs, /api/v1/tools, /mcp      │
│  1. understand: Scope check, security guardrails, period resolution         │
│  2. plan: LLM tool selection (NVIDIA NIM or deterministic fallback)         │
│  3. fetch: monday.com snapshot evaluation (10 min TTL cache, read-only)     │
│  4. normalize: DQ audits, schema normalization, HMAC entity tokenization     │
│  5. compute: Pure DuckDB vectorized analytical execution                    │
│  6. narrate: Numbers-by-reference synthesis using [[F#]] tokens             │
│  7. verify: Numerical tolerance audit, raw digit rejection                  │
│  8. finalize: Entity rehydration, trust receipt, BI blocks assembly         │
└───────────────────────┬───────────────────────────────┬─────────────────────┘
                        │                               │
                        ▼                               ▼
     ┌─────────────────────────────────────┐  ┌───────────────────────────────┐
     │           DUCKDB ENGINE             │  │   BLINDFOLD PRIVACY GATEWAY   │
     │  In-process columnar SQL templates  │  │  HMAC-SHA256 surrogate tokens │
     │  Zero LLM mental math (<15ms query) │  │  Session-scoped in-memory map │
     │  Ground truth: 332 deals, 176 WOs   │  │  Zero raw PII to inference API│
     └─────────────────────────────────────┘  └───────────────────────────────┘
```

### 2.1 Single-Screen Web Interface
- **Source Badge**: Displays live connection status: `monday.com · synced HH:MM · as of 15 Jan 2026`. If the backend is unreachable, it indicates `source disconnected · offline` and presents an error banner.
- **Empty State**: Displays 4 to 6 starter suggestion chips for key operational questions.
- **Live Run Panel**: Visualizes pipeline stages in real time (`understand`, `plan`, `fetch`, `normalize`, `compute`, `narrate`, `verify`, `finalize`). Upon completion, it automatically collapses into a single summary line (`8 stages · 2.4s · 1 tool · 9 rows`) with an explicit `Replay` button.
- **Generated BI Blocks**: Modular blocks produced exclusively from tool outputs:
  - `text`: Verified narrative commentary with `[[F#]]` references resolved.
  - `kpi`: Metric cards showing label, value, display unit, and delta.
  - `chart`: Client-rendered Apache ECharts (bar, line, funnel, waterfall) built directly from tool series data.
  - `table`: Structured tabular data capped at 10 rows.
  - `note`: Operational assumptions, data quality alerts, and caveats.
  - `receipt`: Audit trail displaying SQL query executed, rows scanned, exclusions, and latency.
  - `chips`: Contextual follow-up suggestions.

### 2.2 Deterministic Analytical Tools Engine
All metric computations are executed by DuckDB SQL templates. The LLM never performs arithmetic:
- **Pipeline Summary**: Evaluates 49 open deals (₹68.82 Cr), detects tender outlier concentration (77.3%), and isolates non-tender pipeline (₹15.62 Cr).
- **Revenue Realization Ladder**: Tracks 176 operational work orders: Contracted value excluding GST (₹21.16 Cr), Billed revenue excluding GST (₹10.74 Cr), Realization rate (50.74%), Cash collected including GST (₹9.04 Cr), and Net receivables (₹3.63 Cr).
- **Cross-Board Linkage**: Explicitly refuses direct item-level joins between sales deals and work orders due to lack of a shared primary key (DQ015), reconciling exclusively across 9 canonical sectors.
- **Data Quality Ledger**: Audits anomalies DQ001 through DQ016, including 11 negative credit note adjustments (DQ009) and 15 completed orders with ₹0 billed.

---

## 3. Canonical Tools Catalog

| Tool Name | Scope & Function | Ground Truth Facts |
|---|---|---|
| `pipeline_summary` | Open commercial pipeline aggregation & outlier isolation | 49 open deals, ₹68.82 Cr total pipeline, ₹15.62 Cr non-tender |
| `revenue_waterfall` | Realization ladder from contracted to collected cash | ₹21.16 Cr contracted (excl. GST), ₹10.74 Cr billed (excl. GST), ₹9.04 Cr collected (incl. GST) |
| `sector_performance` | Cross-board analysis across 9 canonical sectors | Energy grouping (Power, Renewables, Utilities) |
| `data_debt_ledger` | Systemic audits across DQ001 through DQ016 | 11 negative credit note adjustments, 15 ₹0 billed completed orders |
| `credit_risk` | Net receivables & payment exposure by account | ₹3.63 Cr net receivables across 11 credit rows |
| `aging_analysis` | Aging distribution of uncollected invoices | Breakdown across 0-30, 31-60, 61-90, 90+ days |
| `client_concentration` | Revenue & pipeline concentration by top accounts | Top counterparty exposure and dependency ratios |
| `deal_slippage` | Close-date slippage and stale deal analysis | Identification of deals slipping across quarters |
| `collection_efficiency` | Cash collection velocity vs. contractual billing terms | Ratio of collections to billings across work orders |
| `margin_analysis` | Service line profitability and operational margin | Work order execution cost vs. billed revenue |
| `conversion_velocity` | Win rates and cycle time by deal stage | Realized win metrics across 64 valued won deals (₹9.50 Cr) |
| `unbilled_exposure` | Operational work orders with zero invoicing | 15 completed orders with ₹0 billed |
| `reconciliation_ledger` | Billing vs. collection ledger balancing | Net ledger variance audits |
| `cross_board_linkage` | Sector-level commercial-to-operational reconciliation | Refuses direct key joins (DQ015); aggregates at sector level |

---

## 4. monday.com Integration & Read-Only Governance

Blindfold BI interfaces with monday.com boards through its GraphQL v2 API:
- **Deals Funnel Board**: Synchronizes commercial opportunity stages, probability weights, values, and close dates.
- **Work Orders Tracker Board**: Synchronizes operational execution statuses, contracted amounts, invoiced amounts, and collections.

### Strict Read-Only Governance
- **Zero GraphQL Mutations**: The backend only executes read queries (`boards`, `items_page`). Any attempt to issue a mutation triggers a `MutationForbiddenError`.
- **Automated CI Guard**: The script `scripts/ci_local.sh` checks for mutation references in `backend/app/` and fails the build if any are detected.
- **Snapshot Caching**: Data is cached in-memory with a 10-minute TTL and single-flight background re-sync to prevent upstream rate limiting.
- **Data Isolation**: Raw spreadsheet files (`.xlsx`) exist only inside `backend/tests/fixtures/` for automated unit tests. They are excluded from Docker images via `.dockerignore`.

---

## 5. Environment Variables

The application is configured using environment variables in `backend/.env` or system environment:

| Variable | Type | Default | Description |
|---|---|---|---|
| `API_KEY` | string | `skylark-secret-v1-key` | API key required for protected REST endpoints |
| `LLM_MODE` | string | `on` | Set to `off` to run pipeline with local deterministic synthesis |
| `NVIDIA_API_KEY` | string | `""` | API key for NVIDIA NIM Llama-3.3-70B model inference |
| `NVIDIA_BASE_URL` | string | `https://integrate.api.nvidia.com/v1` | Base URL for NVIDIA NIM inference |
| `MONDAY_API_KEY` | string | `""` | monday.com API token (falls back to cached snapshot if unset) |
| `MONDAY_DEALS_BOARD_ID` | string | `""` | Board ID for commercial deals |
| `MONDAY_WORKORDERS_BOARD_ID` | string | `""` | Board ID for operational work orders |
| `RATE_LIMIT_PER_MINUTE` | int | `60` | Maximum requests per minute per IP |
| `CORS_ORIGINS` | list | `["*"]` | Allowed CORS origins for the API |

For the frontend (`frontend/.env`):

| Variable | Type | Default | Description |
|---|---|---|---|
| `VITE_API_BASE` | string | `http://127.0.0.1:8000` | Backend API base URL (set to Azure Container App URL in prod) |

---

## 6. API Overview

### 6.1 REST Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/chat` | None | Initiates SSE stream for conversational query |
| `GET` | `/api/v1/runs/{run_id}` | None | Retrieves final result payload and replay trace of a run |
| `GET` | `/api/v1/meta/source` | None | Returns data source sync status, timestamps, and row counts |
| `GET` | `/api/v1/tools` | API Key | Returns tool catalog with JSON schemas |
| `GET` | `/api/v1/tools/starter-chips` | None | Returns starter suggestion chips for initial empty state |
| `GET` | `/api/v1/tools/{name}/schema` | API Key | Returns JSON schema for a specific tool |
| `POST` | `/api/v1/tools/{name}` | API Key | Executes a tool directly with arguments |
| `POST` | `/api/v1/data/refresh` | API Key | Triggers read-only refresh of cached data snapshot |
| `GET` | `/healthz` | None | Liveness check |
| `GET` | `/readyz` | None | Readiness check (validates database and configuration) |
| `POST` | `/mcp` | None | Model Context Protocol JSON-RPC 2.0 endpoint |

### 6.2 Server-Sent Events (SSE) Protocol

Streaming responses from `POST /api/v1/chat` emit typed JSON events:

| Event | Description | Key Payload Attributes |
|---|---|---|
| `run.started` | Pipeline execution initiated | `run_id`, `question`, `as_of`, `source` |
| `stage` | Transition in stage lifecycle | `name`, `status` (`running`/`done`/`warn`/`error`), `started_at`, `duration_ms`, `meta` |
| `tool` | Analytical tool invocation | `name`, `args`, `rows_in`, `rows_out`, `excluded`, `duration_ms` |
| `llm` | LLM invocation | `call`, `model`, `tokens_in`, `tokens_out`, `duration_ms`, `degraded` |
| `answer` | Final payload with generated BI blocks | `blocks[]`, `receipt`, `chips[]`, `clarification` |
| `run.finished` | Execution complete | `total_ms`, `degraded` |
| `run.error` | Execution failure | `code`, `message`, `retryable` |

---

## 7. Cloud Deployment (Microsoft Azure)

The production stack is deployed across Azure infrastructure:
- **Frontend**: Azure Static Web Apps (`skylark-bi-frontend` in `rg-blindfold-bi-central`) serving the compiled React 19 single-screen bundle at [https://mango-plant-08ea0340f.1.azurestaticapps.net](https://mango-plant-08ea0340f.1.azurestaticapps.net).
- **Backend API**: Azure Container Apps (`skylark-bi-api` in `rg-blindfold-bi-central`) running FastAPI at [https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io](https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io).
- **Container Registry**: Azure Container Registry (`skylarkbicr.azurecr.io`).

### 7.1 Automated CI/CD via GitHub Actions

The repository includes `.github/workflows/deploy-azure.yml` which automatically triggers on every push to `main`:
1. **Quality Gate**: Runs backend pytest evals with zero-math-drift assertions and builds the React bundle.
2. **Deploy UI**: Deploys the frontend to Azure Static Web Apps using `AZURE_STATIC_WEB_APPS_API_TOKEN`.
3. **Deploy Backend**: Builds the Docker container via Azure Container Registry and updates the Azure Container App using `ACR_PASSWORD` and `AZURE_CREDENTIALS`.

To configure automatic deployments, add the following secrets in GitHub (**Settings > Secrets and variables > Actions**):
- `AZURE_STATIC_WEB_APPS_API_TOKEN`: Deployment token from `az staticwebapp secrets list --name skylark-bi-frontend --resource-group rg-blindfold-bi-central`.
- `ACR_PASSWORD`: Access password from `az acr credential show --name skylarkbicr`.
- `AZURE_CREDENTIALS`: Service principal credentials from `az ad sp create-for-rbac`.

### 7.2 Manual CLI Deployment

Deployments can also be executed directly via Azure CLI:

```bash
# 1. Build & Deploy Backend Container
az acr build --registry skylarkbicr --image skylark-backend:latest .
az containerapp update \
  --name skylark-bi-api \
  --resource-group rg-blindfold-bi-central \
  --image skylarkbicr.azurecr.io/skylark-backend:latest

# 2. Build & Deploy Frontend Client
cd frontend
VITE_API_BASE="https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io" npm run build
npx @azure/static-web-apps-cli deploy ./dist \
  --app-name skylark-bi-frontend \
  --resource-group rg-blindfold-bi-central \
  --env production
```

---

## 8. Local Setup & Verification

### Prerequisites
- Python 3.12 or 3.13
- Node.js 20+ and npm

### 8.1 Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 8.2 Frontend Setup
```bash
cd frontend
npm install
npm run build
npm run preview -- --host 127.0.0.1 --port 3000
```

### 8.3 Running Local Continuous Integration
Execute the local CI verification script to check repository hygiene, read-only rules, unit tests, and production build:
```bash
./scripts/ci_local.sh
```

### 8.4 Running Acceptance Tests
1. **Real-Time Stream Verification**:
   ```bash
   curl -N -X POST http://127.0.0.1:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -d '{"session_id":"test","question":"How is the energy pipeline this quarter?"}'
   ```
2. **Metadata Source Status**:
   ```bash
   curl http://127.0.0.1:8000/api/v1/meta/source
   ```
3. **Playwright End-to-End Test Suite**:
   ```bash
   python scripts/test_e2e_playwright.py
   ```
4. **Schemathesis OpenAPI Contract Fuzzing**:
   ```bash
   schemathesis run http://127.0.0.1:8000/openapi.json \
     --checks all --header "X-API-Key: skylark-secret-v1-key"
   ```
