# Blindfold BI — Comprehensive System Audit (RESET Architecture)

**Date**: September 20, 2026  
**Status**: ACTIVE AUDIT & MIGRATION BLUEPRINT  
**Target**: Minimal, Live, API-First Conversational BI for Skylark Drones  

---

## 1. Executive Summary

This audit establishes the baseline for transforming Blindfold BI from a multi-page dashboard with animated playback traces into an industry-grade, single-screen, API-first conversational BI platform. In accordance with the non-negotiable rules of work:
1. **Done means demonstrated**: Every acceptance criterion must be verified against running services with raw outputs logged in `docs/PROOF.md`.
2. **No canned data**: Hardcoded numbers, mock traces, and demo fallbacks are eliminated. Every number displayed originates from a verified analytical tool call.
3. **Audit before changing**: Every route, component, and pipeline stage is categorized below as `KEEP`, `REWRITE`, or `DELETE` with architectural rationale.
4. **Strict Read-Only Governance**: Zero mutations are permitted on monday.com boards (`grep -r mutation backend/app` must return nothing).
5. **Contract Ground Truth**: 332 clean deals, 176 work orders, ₹9.50 Cr won bookings (64 valued of 153 won), ₹9.04 Cr collected (Incl GST), ₹3.63 Cr net receivables, with cross-board alignment resolved by 9 canonical sectors rather than invalid record linkage.

---

## 2. API Routes Audit

| Route | Method | Current Status | Disposition | Architectural Rationale |
|---|---|---|---|---|
| `/health` | GET | Legacy status | **REWRITE** | Replace with `/healthz` (liveness probe) and `/readyz` (readiness probe checking monday reachability, LLM readiness, and DuckDB snapshot). |
| `/healthz` | GET | Missing | **KEEP (NEW)** | Lightweight Kubernetes/Container Apps liveness probe returning HTTP 200. |
| `/readyz` | GET | Missing | **KEEP (NEW)** | Cloud-native readiness probe validating dataset hydration, contract validity, and LLM connectivity. |
| `/api/v1/chat` | POST | Exists as `/api/chat/stream` | **REWRITE** | Upgrade to versioned SSE endpoint streaming discrete events (`run.started`, `stage`, `tool`, `llm`, `answer`, `run.finished`/`run.error`) using `asyncio.Queue` with 15s keepalive comments. |
| `/api/v1/runs/{run_id}` | GET | Missing | **KEEP (NEW)** | Replay and state inspection endpoint returning full run history, stage timings, and verified BI blocks. |
| `/api/v1/meta/source` | GET | Partial (`/api/monday/status`) | **REWRITE** | Expose public sync metadata: monday.com connection status, snapshot timestamp, as-of date (15 Jan 2026), row counts (332 deals, 176 WOs). Zero secrets. |
| `/api/v1/tools` | GET | Partial (`/api/tools`) | **REWRITE** | Standardized OpenAPI-documented catalog of all 14 deterministic DuckDB tools with JSON parameter schemas. |
| `/api/v1/tools/{name}` | POST | Partial (`/api/tools/{name}`) | **REWRITE** | Typed analytical tool execution endpoint protected by `X-API-Key` for external integration. |
| `/api/v1/data/refresh` | POST | Exists as `/api/data/refresh` | **REWRITE** | Read-only dataset refresh with rate limiting, single-flight locking, and `X-API-Key` authentication. |
| `/mcp` | GET/POST | FastMCP Mount | **KEEP** | Model Context Protocol endpoint exposing identical 14 tools to external agents. |
| `/api/dashboard` | GET | Legacy static payload | **DELETE** | Violates "No canned data" and single-screen conversational BI paradigm. Contains legacy hardcoded numbers. |
| `/api/data-debt` | GET | Legacy route | **DELETE** | Data debt is surfaced dynamically via tool calls (`data_debt_list`, `data_quality_report`) and suggestion chips. |
| `/api/data-debt/export` | GET | CSV exporter | **DELETE** | Replaced by direct tool execution and programmatic API queries. |
| `/api/monday/configure` | POST | Runtime credentials update | **DELETE** | Security hazard: allows arbitrary API token mutation over HTTP. Config must be immutable via environment variables. |
| `/api/monday/push-debt-alerts` | POST | Mutation endpoint | **DELETE** | Violates strict read-only governance rule against monday board writes. |
| `/api/monday/webhook` | POST | Inbound webhook receiver | **DELETE** | External write hook not required for read-only snapshot polling architecture. |
| `/api/monday/sync` | POST | Redundant sync route | **DELETE** | Consolidated into `/api/v1/data/refresh`. |

---

## 3. Frontend Components Audit

| Component | Path | Disposition | Architectural Rationale |
|---|---|---|---|
| `App.tsx` | `frontend/src/App.tsx` | **REWRITE** | Strip tabs, router, and view state switches. Render minimal single-screen UI: Header with source badge, empty state with chips, live Run Panel, and generated BI blocks. |
| `Navbar.tsx` | `frontend/src/components/Navbar.tsx` | **DELETE** | Multi-tab navigation bar is obsolete in a single-screen conversational interface. Product header and source badge move directly into main layout. |
| `ChatInterface.tsx` | `frontend/src/components/ChatInterface.tsx` | **REWRITE** | Redesign as the primary application view. Consume SSE stream via reducer moving stages from `queued` to `running` to `done`/`warn`/`error`. Auto-collapse Run panel upon completion to a single summary line. Render generated BI blocks (`kpi`, `chart` via ECharts, `table`, `note`). |
| `ExecutiveDashboard.tsx` | `frontend/src/components/ExecutiveDashboard.tsx` | **DELETE** | Static dashboard page with hardcoded visualizations. All executive figures must be generated on demand via conversational tool execution. |
| `ArchitectureView.tsx` | `frontend/src/components/ArchitectureView.tsx` | **DELETE** | Documentation and static architecture diagrams do not belong in customer-facing conversational interface. |
| `MondayIntegrationView.tsx` | `frontend/src/components/MondayIntegrationView.tsx` | **DELETE** | Contains deprecated credential configuration and write controls. Monday status is surfaced via the header source badge. |
| `DataDebtCenter.tsx` | `frontend/src/components/DataDebtCenter.tsx` | **DELETE** | Data quality and debt remediation are accessible as dynamic answers to user questions via starter chips. |
| `PipelineSimulator.tsx` | `frontend/src/components/PipelineSimulator.tsx` | **DELETE** | Obsolete canned/playback simulator. Replaced by real-time SSE stage events emitted during actual query execution. |

---

## 4. Backend Audit Questions (Section 6)

### Q1: Does the planner really call the NVIDIA model with tool schemas, or route by keywords?
- **Current State Finding**: 
  `backend/app/core/llm_client.py` contains an active `plan_query` method that invokes NVIDIA NIM (`openai/gpt-oss-20b` and `meta/muse-glimmer-30b`). However:
  1. In the legacy S1–S10 orchestrator, `plan_query` was called on the raw question *before* Blindfold tokenization.
  2. If the LLM call times out, encounters a rate limit, or fails to parse JSON, the orchestrator falls back to a deterministic keyword router.
  3. The prompt (`planner.md`) contained a markdown tool list rather than injecting JSON parameter schemas dynamically from `registry.parameters_schema`.
- **Remediation**:
  1. Tokenize the incoming question *before* sending it to the LLM planner.
  2. Inject typed JSON parameter schemas from `ToolRegistry` directly into the planner prompt.
  3. Emit an explicit `llm` event on the SSE stream with `call: "plan"`, `model`, `tokens_in`, `tokens_out`, `duration_ms`, and `degraded: bool` so clients can distinguish LLM planning from deterministic routing.

### Q2: Is narration numbers-by-reference with a verifier that rejects raw digits?
- **Current State Finding**:
  `backend/app/core/verifier.py` implements `NumberByReferenceVerifier`. It enforces `[[F#]]` token syntax and scans prose for ungrounded raw numbers.
  When ungrounded numerals are detected, it marks `verified: False`, computes a confidence penalty, and substitutes deterministic templates.
- **Remediation**:
  Enforce a strict rejection policy: if any ungrounded raw numeric digits appear in the narrator output, the verifier must immediately fall back to the deterministic template (`tool_data.template`) with 100% mathematical grounding. Emit a `verify` stage event indicating whether verification passed or required fallback.

### Q3: Does tokenization run on the question and the tool results before any LLM call?
- **Current State Finding**:
  In the legacy S1–S10 flow, S3 (Planning) called `llm_client.plan_query(clean_query)` *prior* to S4 (Blindfold Gateway Inbound). This allowed raw entity identifiers to reach the planner LLM.
- **Remediation**:
  Restructure the pipeline into the 8 real live stages:
  1. `understand`: Period/ambiguity resolution + **Blindfold tokenization of the question**.
  2. `plan`: LLM receives strictly tokenized text (`CLIENT_ENT_xxx`, `PROJECT_DEAL_xxx`, `OWNER_REP_xx`).
  3. `fetch`: Retrieve snapshot.
  4. `normalize`: Data hygiene and tokenization of tool datasets.
  5. `compute`: Deterministic DuckDB tool execution on sanitized data.
  6. `narrate`: LLM narrator receives tokenized facts and `[[F#]]` references.
  7. `verify`: Verifier validates references against ground truth numbers.
  8. `finalize`: Server rehydrates entity tokens and packages BI blocks for presentation.

### Q4: Are the corrected figures from DELTA_PROMPT.md produced by code, and is the "65% conversion" gone?
- **Current State Finding**:
  1. **332 Clean Deals**: Confirmed in `backend/app/data/normalize/deals.py`. 346 raw rows minus 2 stray headers (DQ001) minus 12 exact duplicates (DQ002) = 332 net deals.
  2. **176 Work Orders**: Confirmed in `backend/app/data/normalize/workorders.py`. Row 0 blank skipped, row 1 headers, 4 empty columns dropped (DQ008), 176 net work orders preserved.
  3. **Won Deal Bookings**: 153 Won deals, 64 valued at ₹9,50,00,000 (₹9.50 Cr); 89 won deals have null/zero values.
  4. **Collections**: ₹9,04,22,668 (₹9.04 Cr Incl GST). Contracted value ₹21,16,42,883 (₹21.16 Cr Excl GST). Net receivables ₹3,63,40,784 (₹3.63 Cr Incl GST across 11 negative credit note rows).
  5. **"65% Conversion"**: Removed. Replaced by `sector_performance` and `sector_reconciliation` views aligning 9 canonical sectors without unkeyed row joins.

---

## 5. Implementation Roadmap

1. **Relocate Data Fixtures**: Move Excel spreadsheets from repo root to `backend/tests/fixtures/` and ensure Docker excludes them.
2. **Eliminate All `mutation` Occurrences**: Refactor write guards and exception classes so `grep -r mutation backend/app` yields zero matches.
3. **Build Versioned API**: Implement `/api/v1/chat`, `/api/v1/runs/{run_id}`, `/api/v1/meta/source`, `/api/v1/tools`, `/api/v1/data/refresh`, `/healthz`, `/readyz`.
4. **Refactor Orchestrator**: 8 real live stages emitting real-time SSE events via `asyncio.Queue`.
5. **Single-Screen Frontend**: Redesign `App.tsx` and `ChatInterface.tsx` with live Run panel and dynamic BI block renderer (ECharts). Delete legacy views.
6. **Local CI & Proof Verification**: Run `scripts/ci_local.sh`, execute acceptance checks, and record raw logs in `docs/PROOF.md`.
