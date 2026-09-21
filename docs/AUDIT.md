# Blindfold BI — Module Audit (PLAN V3)

**Date**: 21 September 2026
**Auditor**: Automated codebase audit per PLAN V3 §9
**Scope**: Every production module classified as **KEEP**, **REBUILD**, or **DELETE** with rationale.

---

## Legend

| Tag | Meaning |
|---|---|
| **KEEP** | Architecturally sound; survives rebuild with at most minor fixes. |
| **REBUILD** | Right intent, wrong execution; rewrite to PLAN V3 contracts. |
| **DELETE** | Dead code, security hazard, or violates PLAN V3 principles; remove entirely. |

---

## 1. Backend — Core Pipeline

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/core/orchestrator.py` | ~1107 | **REBUILD** | Heart of the pipeline. Current S1–S10 flow must become the 8 real live stages (understand → plan → fetch → normalize → compute → narrate → verify → finalize). Keyword-based planning fallback, pre-tokenization LLM calls (S3 before S4), and the oversized `_build_generated_bi_blocks()` method all need rewriting. SSE event bus coupling and stage naming must align with PLAN V3 §4. |
| `backend/app/core/verifier.py` | 401 | **REBUILD** | `NumberByReferenceVerifier` logic is correct in spirit but the repair loop is missing: current code goes straight from `audit_claims()` failure to `build_question_aware_fallback()`. PLAN V3 requires: reject → one LLM repair attempt → fallback. Regex-based claim scanning is fragile; `ALLOWED_NUMERALS` hard-codes year ranges. `_build_legacy_fallback()` uses hardcoded template strings — delete that method. |
| `backend/app/core/llm_client.py` | 325 | **REBUILD** | Contains `plan_query()` and `narrate()` methods calling NVIDIA NIM. `plan_query()` injects a markdown tool list instead of JSON parameter schemas from `registry.parameters_schema`. Must inject typed tool schemas and operate on tokenized input. |
| `backend/app/core/tokenizer.py` | 185 | **KEEP** | `BlindfoldTokenizer` with `tokenize_text()`, `rehydrate_text()`, `tokenize_obj()`, `rehydrate_obj()`, `check_leakage()`. Architecturally sound. Session-scoped HMAC entity substitution works as intended. |
| `backend/app/core/gateway.py` | 106 | **KEEP** | `BlindfoldGatewayService` managing per-session tokenizers. `init_catalog()` populates entity catalog from DuckDB. Clean design. |
| `backend/app/core/anonymizer.py` | 10 | **KEEP** | Backwards-compat shim re-exporting `gateway.blindfold_gateway`. Harmless, 10 lines. Keep until all import sites are migrated, then delete. |
| `backend/app/core/key_store.py` | 233 | **KEEP** | API key management with Azure Blob backend and local file fallback. Used by `/readyz` and admin endpoints. |
| `backend/app/core/run_store.py` | 29 | **KEEP** | In-memory run history store for `/api/v1/runs/{run_id}`. Minimal, useful. |

---

## 2. Backend — Data Layer

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/data/duckdb_store.py` | 227 | **REBUILD** | **This is the data path drift problem.** `initialize()` loads from xlsx files OR parquet snapshots as fallback. Must be rewired to accept DataFrames from live Monday.com fetch (via `monday_client`) as the primary path, with xlsx fixtures only for tests. The 4 analytical views (`deals`, `work_orders`, `sector_reconciliation`, `deal_wo_lifecycle`) are correct and valuable — preserve their SQL. |
| `backend/app/data/adapter.py` | 66 | **REBUILD** | `DataAdapter` delegates to `duckdb_store.initialize()` but hardcodes `self.source = "monday.com"` regardless of actual data source. `get_status()` returns fallback counts `332`/`176` when data is `None`. Must: (1) actually call `MondayClient.fetch_all_items()` when token is configured, (2) honestly report source, (3) pass fetched DataFrames to DuckDBStore. |
| `backend/app/data/monday_client.py` | 239 | **KEEP** | Well-structured async GraphQL client with `WriteForbiddenError`, cursor-paginated `fetch_all_items()`, `CallBudgetExceededError` (800/day). **Problem**: This client exists and works but is NOT wired into the data pipeline. REBUILD of `adapter.py` must wire this in as the primary data source. |
| `backend/app/data/snapshot.py` | 91 | **DELETE** | `SnapshotService` duplicates `adapter.py` + `duckdb_store.py` loading logic (xlsx → parquet fallback). Not used in the main pipeline (`adapter.py` uses `duckdb_store` directly). Dead code that masks the real data path. |
| `backend/app/data/db.py` | 21 | **KEEP** | Thin `Database` wrapper around `duckdb_store`. Harmless shim used by `main.py` for `init_db()`. |
| `backend/app/data/cleaner.py` | 163 | **KEEP** | `clean_deals_data()`, `clean_work_orders_data()`. Imported by `adapter.py`. Normalization helpers. |
| `backend/app/data/dq_ledger.py` | 88 | **KEEP** | DQ anomaly ledger. In-memory list of `DQEntry` objects with add/query/clear. Used by tools and snapshot service. |
| `backend/app/data/normalize/__init__.py` | — | **KEEP** | Re-exports `normalize_deals`, `normalize_work_orders`. |
| `backend/app/data/normalize/common.py` | 75 | **KEEP** | Shared normalization constants including `DEFAULT_AS_OF_DATE = "15 Jan 2026"`, column aliases, sector mappings. |
| `backend/app/data/normalize/deals.py` | 198 | **KEEP** | DQ001 (stray header), DQ002 (duplicates), DQ003 (null values) normalization. Produces 332 clean deals. |
| `backend/app/data/normalize/workorders.py` | 244 | **KEEP** | DQ008 (empty columns), DQ014 (unbilled nulls) normalization. Produces 176 clean work orders. |
| `backend/app/data/snapshots/deals_snapshot.parquet` | — | **DELETE** | Parquet snapshot file. PLAN V3: "No xlsx, parquet, or seed data in production code or the image; fixtures only in `backend/tests/fixtures/` for tests." |
| `backend/app/data/snapshots/wo_snapshot.parquet` | — | **DELETE** | Same as above. |
| `backend/app/integrations/monday_client.py` | 167 | **DELETE** | Duplicate of `backend/app/data/monday_client.py` (same `MondayClient` class, `WriteForbiddenError`, `MutationForbiddenError`). Two copies of the same client in different packages. Keep `data/monday_client.py`, delete this one. Fix any imports. |

---

## 3. Backend — Tools

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/tools/registry.py` | 402 | **KEEP** | `ToolRegistry` with 16 tools across 6 domains, Python dispatch, REST router, FastMCP registration, `ToolDefinition` auto-schema. Pattern is solid. Rebuild only the tool implementations it calls. |
| `backend/app/tools/pipeline_tools.py` | ~716 | **REBUILD** | `pipeline_summary()`, `win_loss_analysis()`, `owner_performance()`. Tools return `ToolResult` with Facts, Tables, ChartSpecs, DQ entries — correct contract. But: Tender concentration special-case branching is fragile; hardcoded display strings; some SQL not parameterized. Rebuild to cleaner parameterized SQL with consistent ToolResult construction. |
| `backend/app/tools/revenue_tools.py` | ~693 | **REBUILD** | `revenue_ladder()`, `receivables_summary()`, `sector_performance()`. Same pattern: correct ToolResult contract, but metric branching (`if metric == "collected_cash"`) is ad-hoc, and hardcoded display formatting. Rebuild with consistent ToolResult construction. |
| `backend/app/tools/operations_tools.py` | ~570 | **REBUILD** | `workorder_health()`, `link_deals_to_orders()`. Backwards-compat wrappers present. DQ010/DQ011/DQ015 logic is valuable but implementation is verbose and brittle. |
| `backend/app/tools/query_tools.py` | 333 | **REBUILD** | `data_quality_report()`, `data_debt_list()`. DQ001–DQ016 scorecard is the right shape. `data_debt_list` has direct SQL for stale deals — good but needs cleanup. |
| `backend/app/tools/executive_tools.py` | 613 | **REBUILD** | `leadership_brief()`: synthesizes 4 tools — correct pattern but the aggregation is brittle. `compare_periods()`: parameterized SQL delta — keep logic. `explain_metric()`: fuzzy YAML lookup — good. `list_capabilities()`: static catalog — keep. **`get_executive_brief()`**: backwards-compat wrapper with HARDCODED business values (wins, risks, recommendations, deltas) — **DELETE this function specifically**. |
| `backend/app/tools/chips.py` | 174 | **KEEP** | `STARTER_CHIPS` list and deterministic chip generation. Clean, used by orchestrator for suggestion chips. |
| `backend/app/tools/receipt.py` | 113 | **KEEP** | `calculate_confidence()` and trust receipt generator. Cryptographic audit provenance for tool calls. |
| `backend/app/tools/period_resolver.py` | 247 | **KEEP** | Indian fiscal year period parsing (Q4 FY25-26 = Jan–Mar 2026). Valuable, correct logic. |

---

## 4. Backend — API Layer

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/main.py` | 194 | **KEEP** | FastAPI app with lifespan, CORS, request tracing middleware, `/healthz`, `/readyz`, MCP mount, v1 router. Minor fix needed: CORS `["*"]` must be tightened per PLAN V3. |
| `backend/app/api/v1/router.py` | ~20 | **KEEP** | Aggregated v1 router. Clean. |
| `backend/app/api/v1/chat.py` | — | **KEEP** | SSE chat endpoint. May need minor adjustments when orchestrator is rebuilt. |
| `backend/app/api/v1/runs.py` | — | **KEEP** | Run history endpoint (`/api/v1/runs/{run_id}`). |
| `backend/app/api/v1/meta.py` | — | **KEEP** | Source metadata endpoint. |
| `backend/app/api/v1/tools.py` | — | **KEEP** | Tool execution REST endpoint. Uses `registry.execute_tool()`. |
| `backend/app/api/v1/data.py` | — | **KEEP** | Data refresh endpoint. Needs rate limiting/auth review. |
| `backend/app/api/v1/admin_keys.py` | — | **KEEP** | Admin key management. Protected by `ADMIN_TOKEN`. |
| `backend/app/api/v1/deps.py` | — | **KEEP** | Shared dependencies, `ProblemException` (RFC 7807). |
| `backend/app/api/v1/__init__.py` | — | **KEEP** | Re-exports `api_v1_router`. |

---

## 5. Backend — Models & Contracts

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/contracts.py` | 266 | **KEEP** | `ToolResult`, `Fact`, `Table`, `ChartSpec`, `DQEntry`, `Receipt`, `StructuredIntent`, `ChipCandidate`, `ContractManager`. Core contract dataclasses. Ground truth definitions. |
| `backend/app/models/v1.py` | 299 | **KEEP** | Pydantic v1 API response models. |
| `backend/app/models/schemas.py` | 74 | **KEEP** | Legacy schemas. May merge into `v1.py` during cleanup. |

---

## 6. Backend — Events & MCP

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/events/bus.py` | 123 | **REBUILD** | `StepEvent` uses S1–S10 naming. Must align with the 8-stage pipeline naming from PLAN V3. SSE emission logic (`asyncio.Queue`, keepalive) is reusable. |
| `backend/app/mcp/server.py` | 169 | **KEEP** | FastMCP server registration. Tools auto-registered from `registry`. Clean. |
| `backend/app/mcp/__init__.py` | — | **KEEP** | Package init. |

---

## 7. Backend — Prompts

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/prompts/planner.md` | 51 | **REBUILD** | 14-tool routing rules with parameter extraction. Must inject JSON parameter schemas from `registry.parameters_schema` dynamically instead of a static markdown list. Output schema is correct. |
| `backend/app/prompts/narrator.md` | — | **REBUILD** | Numbers-by-reference narrator prompt. Must enforce PLAN V3 §5 response structure: Direct Answer → Evidence bullets → Caveats. No recommendations section. Must explicitly instruct `[[F#]]` token usage for every quantitative claim. |

---

## 8. Backend — Configuration & Security

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `backend/app/config.py` | 57 | **REBUILD** | `DEALS_EXCEL_PATH` and `SNAPSHOT_*_PARQUET` hardcoded — must be test-only fallbacks, not the primary data path. Default dev secrets (`API_KEY = "skylark-secret-v1-key"`, `ADMIN_TOKEN = "dev-admin-token-super-secret-12345"`) are acceptable for local dev but must never reach production (env var override is present). `CORS_ORIGINS: ["*"]` must be tightened. Add `MONDAY_DATA_SOURCE_PRIORITY` setting (live → snapshot → fixture). |

---

## 9. Frontend

| Module | Lines | Disposition | Reason |
|---|---|---|---|
| `frontend/src/App.tsx` | 215 | **REBUILD** | Two-tab layout (Agent \| Info) is correct per PLAN V3. But source badge, theme toggle, and SSE consumption need alignment with the rebuilt orchestrator's 8-stage event stream. |
| `frontend/src/components/ChatInterface.tsx` | 562 | **REBUILD** | Primary chat view. SSE reducer, message rendering, BI block display. Must consume the 8-stage events (not S1–S10), auto-collapse Run panel on completion, render `kpi`/`chart`/`table`/`note` BI blocks. |
| `frontend/src/components/RunPanel.tsx` | 251 | **REBUILD** | Pipeline stage visualization. Currently wired to S1–S10 step events. Must display 8 stages with `queued → running → done/warn/error` transitions. |
| `frontend/src/components/BiBlocksRenderer.tsx` | 156 | **KEEP** | Renders BI blocks (KPI cards, charts, tables, notes). Correct structure. Minor tweaks for new block shapes. |
| `frontend/src/components/EChartRenderer.tsx` | 96 | **KEEP** | ECharts wrapper. Clean. |
| `frontend/src/components/InfoTab.tsx` | 634 | **REBUILD** | Info/documentation tab. Overgrown at 634 lines. Trim to essential system info, data source status, and tool catalog. Remove any hardcoded business metrics. |
| `frontend/src/types.ts` | — | **KEEP** | TypeScript type definitions. Update when event shapes change. |
| `frontend/src/apiConfig.ts` | — | **KEEP** | API URL configuration. |
| `frontend/src/main.tsx` | — | **KEEP** | React entry point. |
| `frontend/src/App.css` | — | **KEEP** | Global styles. |
| `frontend/src/index.css` | — | **KEEP** | Base styles. |

---

## 10. Infrastructure & CI/CD

| Module | Disposition | Reason |
|---|---|---|
| `infra/main.json` | **KEEP** | Azure ARM template for Container Apps deployment. |
| `.github/workflows/ci-cd.yml` | **KEEP** | CI pipeline. |
| `.github/workflows/deploy-azure.yml` | **KEEP** | Azure deployment workflow. |
| `Dockerfile` | **KEEP** | Docker build. Verify `.dockerignore` excludes xlsx/parquet/snapshots. |
| `.dockerignore` | **KEEP** | Must exclude `*.xlsx`, `*.parquet`, `data/snapshots/`. |
| `frontend/staticwebapp.config.json` | **KEEP** | Azure Static Web Apps config. |
| `frontend/public/staticwebapp.config.json` | **KEEP** | Same, public copy. |

---

## 11. Contracts (YAML Ground Truth)

| File | Disposition | Reason |
|---|---|---|
| `contracts/metric_contract.yaml` | **KEEP** | Master metric definitions, formulas, SQL, business logic. |
| `contracts/metrics.yaml` | **KEEP** | Metric governance lookup for `explain_metric()`. |
| `contracts/sectors.yaml` | **KEEP** | 9 canonical sectors with alias mappings. |
| `contracts/periods.yaml` | **KEEP** | Indian fiscal year period definitions. |
| `contracts/stages.yaml` | **KEEP** | Deal stage definitions. |
| `contracts/ambiguity.yaml` | **KEEP** | Ambiguous term resolution rules. |
| `contracts/schema_map.yaml` | **KEEP** | Monday.com column-to-schema mappings. |

---

## 12. Tests

| Module | Disposition | Reason |
|---|---|---|
| `backend/tests/test_verifier.py` | **KEEP** | Verifier unit tests. Update when verifier is rebuilt. |
| `backend/tests/test_duckdb_tools.py` | **KEEP** | DuckDB analytical tool tests. |
| `backend/tests/test_tools_contract.py` | **KEEP** | ToolResult contract conformance tests. |
| `backend/tests/test_data_layer.py` | **KEEP** | Data normalization tests. |
| `backend/tests/test_monday_integration.py` | **KEEP** | Monday.com client tests with `FakeMondayTransport`. |
| `backend/tests/test_anonymizer.py` | **KEEP** | Blindfold tokenizer tests. |
| `backend/tests/test_golden_evals.py` | **KEEP** | Golden answer evaluation tests. |
| `backend/tests/evals/oracle.py` | **KEEP** | Evaluation oracle. |
| `backend/tests/fixtures/*.xlsx` | **KEEP** | Test fixtures. These are the ONLY place xlsx files belong. |

---

## 13. Scripts & Documentation

| File | Disposition | Reason |
|---|---|---|
| `scripts/answer_audit.py` | **REBUILD** | Answer quality audit script. Align with rebuilt verifier and 8-stage pipeline. |
| `scripts/profile_data.py` | **KEEP** | Dataset profiling. Ground truth verification. |
| `scripts/ci_local.sh` | **KEEP** | Local CI runner. |
| `scripts/verify_credentials.py` | **KEEP** | Credential verification utility. |
| `scripts/keys.sh` | **KEEP** | Key management helper. |
| `scripts/set_azure_secrets.sh` | **KEEP** | Azure secret provisioning. |
| `scripts/test_e2e_playwright.py` | **KEEP** | E2E tests. |
| `backend/evals/questions.yaml` | **KEEP** | Evaluation question bank. |
| `backend/evals/run_eval.py` | **KEEP** | Evaluation runner. |
| `backend/scripts/probe_models.py` | **KEEP** | LLM model probing utility. |
| `docs/AUDIT.md` | **REBUILD** | This file. Rewritten per PLAN V3. |
| `docs/DATA_NOTES.md` | **KEEP** | Data provenance notes. |
| `docs/PROOF.md` | **KEEP** | Acceptance proof logs. |
| `CLAUDE.md` | **KEEP** | Project instructions for Claude Code. |
| `DECISION_LOG.md` | **KEEP** | Architectural decision log. |
| `README.md` | **REBUILD** | Must reflect PLAN V3 architecture, not the old dashboard-oriented description. |
| `storage/keys.json` | **KEEP** | Local key store fallback. Excluded from git via `.gitignore`. |

---

## 14. Summary Counts

| Disposition | Count | Notes |
|---|---|---|
| **KEEP** | 52 | Architecturally sound or reusable. |
| **REBUILD** | 19 | Core pipeline, data adapter, tools, prompts, frontend views, docs. |
| **DELETE** | 4 | `snapshot.py`, 2× parquet files, duplicate `integrations/monday_client.py`. |

---

## 15. Critical Path (Build Order per PLAN V3 §10)

```
Phase 1: Live Data Path
  REBUILD  adapter.py          → wire MondayClient as primary source
  REBUILD  duckdb_store.py     → accept live DataFrames, keep analytical views
  REBUILD  config.py           → add MONDAY_DATA_SOURCE_PRIORITY
  DELETE   snapshot.py         → remove dead code
  DELETE   data/snapshots/*.parquet  → remove from production image
  DELETE   integrations/monday_client.py → remove duplicate

Phase 2: Agent Core
  REBUILD  orchestrator.py     → 8 real live stages
  REBUILD  verifier.py         → reject → repair → fallback loop
  REBUILD  llm_client.py       → inject typed tool schemas
  REBUILD  events/bus.py       → 8-stage event naming
  REBUILD  planner.md          → dynamic JSON schemas
  REBUILD  narrator.md         → PLAN V3 §5 response structure

Phase 3: Tools
  REBUILD  pipeline_tools.py   → clean parameterized SQL, consistent ToolResult
  REBUILD  revenue_tools.py    → same
  REBUILD  operations_tools.py → same
  REBUILD  query_tools.py      → same
  REBUILD  executive_tools.py  → delete get_executive_brief(), clean rest

Phase 4: Frontend
  REBUILD  App.tsx             → align with 8-stage SSE
  REBUILD  ChatInterface.tsx   → consume 8-stage events, BI blocks
  REBUILD  RunPanel.tsx        → 8 stages, not S1-S10
  REBUILD  InfoTab.tsx         → trim to essentials

Phase 5: Docs & Polish
  REBUILD  README.md           → PLAN V3 architecture
  REBUILD  answer_audit.py     → align with rebuilt verifier
  KEEP     config.py CORS      → tighten from ["*"] to explicit origins
```

---

## 16. Security Invariants (MUST preserve verbatim per PLAN V3)

1. "Secrets (NVIDIA key, monday token, board IDs) live in Container App secrets, never in GitHub or the frontend."
2. "No xlsx, parquet, or seed data in production code or the image; fixtures only in `backend/tests/fixtures/` for tests."
3. "No GraphQL `mutation` is permitted." Unit tests enforce zero mutations in `backend/app`.
4. Read-only Monday.com guard enforced via dynamic keyword detection (`WriteForbiddenError`).
5. Blindfold Gateway: Entity identifiers tokenized with session-scoped HMAC salts before prompts reach any LLM.
6. CORS origins must be tightened from `["*"]` to explicit allowed origins.
7. Default dev secrets (`API_KEY`, `ADMIN_TOKEN`) acceptable for local dev only; production must override via env vars.
