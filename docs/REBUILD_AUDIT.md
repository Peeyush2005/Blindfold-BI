# BLINDFOLD BI — DEEP REBUILD AUDIT & GAP ANALYSIS
**Document Version**: 1.0.0  
**Date**: September 2026  
**Repository**: `https://github.com/Peeyush2005/Blindfold-BI`  
**Production Endpoints**:
- **Frontend**: `https://mango-plant-08ea0340f.1.azurestaticapps.net/`
- **Backend API**: `https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io`
- **MCP Server**: `https://skylark-bi-api.orangecliff-665a6258.centralus.azurecontainerapps.io/mcp`

---

## 1. Executive Summary

Blindfold BI is an API-first, conversational business intelligence platform built for Skylark Drones with a strict security and anti-hallucination invariant: **The Large Language Model (LLM) never directly accesses raw commercial business data**. All analytical calculations are performed deterministically in DuckDB and exposed via typed Model Context Protocol (MCP) tools. The narrator receives only schema definitions and pseudonymized tool results, authoring responses using fact reference tokens (`[[F#]]`), which a server-side verifier validates before substituting grounded numbers and rehydrating entity identities.

This audit evaluates the codebase against the **Complete Rebuild Master Prompt** requirements, identifying existing architectural strengths to preserve, foundational gaps to close, and a step-by-step roadmap to transform the system into the **Executive Intelligence Workspace**.

---

## 2. Current Architecture

```
                                  ┌────────────────────────────────────────────────┐
                                  │           EXECUTIVE CLIENT (React)             │
                                  │   (Desktop 3-Column / Mobile Responsive)       │
                                  └───────────────────────┬────────────────────────┘
                                                          │ SSE Stream / REST
                                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI APPLICATION SERVER (backend/app)                                         │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │ AGENT ORCHESTRATOR (backend/app/core/orchestrator.py)                    │   │
│   │  Stages: S1 Intake -> S2 Understand -> S3 Plan -> S4 Blindfold-in        │   │
│   │          -> S5 Tools -> S6 Blindfold-out -> S7 Narrate -> S8 Verify      │   │
│   │          -> S9 Re-identify -> S10 Render                                 │   │
│   └───────────────────────────────┬──────────────────────────────────────────┘   │
│                                   │                                              │
│         ┌─────────────────────────┴────────────────────────┐                     │
│         ▼                                                  ▼                     │
│   ┌───────────────────────────┐                      ┌───────────────────────┐   │
│   │ BLINDFOLD PRIVACY GATEWAY │                      │ FASTMCP SERVER (/mcp) │   │
│   │ Session HMAC Pseudonymize │                      │ Typed Tool Registry   │   │
│   └───────────────────────────┘                      └───────────┬───────────┘   │
│                                                                  │               │
│                                                                  ▼               │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │ DETERMINISTIC DATA LAYER (backend/app/data)                              │   │
│   │  DuckDB In-Memory Engine + DataAdapter (monday.com REST + Local Snapshot)│   │
│   │  Strict Read-Only Enforcement (Zero GraphQL Mutations)                   │   │
│   │  Data Quality Ledger (DQ001 - DQ016)                                     │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Key Components:
1. **Core Orchestrator (`backend/app/core/orchestrator.py`)**: Coordinates prompt ingestion, tool execution planning, pseudonymization, narration generation with LLM (NVIDIA NIM or deterministic fallback), reference token verification, and SSE event streaming.
2. **Deterministic DuckDB Store (`backend/app/data/db.py`)**: Stores cleaned tables `deals_analytic` and `work_orders_analytic` with comprehensive view definitions.
3. **Data Adapter (`backend/app/data/adapter.py`)**: Implements monday.com API integration with 10-minute caching and automatic fallback to verified Excel snapshot fixtures.
4. **Tool Registry & FastMCP (`backend/app/tools/registry.py`)**: Bridges DuckDB analytic functions to FastMCP server (`/mcp`) and REST API (`/api/v1/tools`).
5. **Numerical Verifier (`backend/app/core/verifier.py`)**: Verifies fact tokens (`[[F#]]` or `[F#]`) against extracted tool evidence values within a 1.0% tolerance, replacing them with formatted strings or falling back to safe templates.
6. **Frontend (`frontend/src`)**: Single-page application in React 18, TypeScript, TailwindCSS, and Lucide icons.

---

## 3. Existing Strengths

1. **Strict Data Firewall**:
   - Raw data tables are physically shielded from model prompts.
   - LLMs only interact with tool JSON schemas and aggregated surrogate records.
2. **Deterministic Arithmetic**:
   - All sums, conversions, weighted averages, and DSO calculations execute in DuckDB SQL; zero arithmetic is delegated to LLM mental math.
3. **Read-Only Monday.com Governance**:
   - Zero GraphQL mutations exist in `backend/app`. Test suites rigorously enforce that only read queries (`query { boards(...) }`) are permitted.
4. **Resilient Data Quality Ledger**:
   - Active detection for stray header rows (DQ001), duplicate records (DQ002), null deal values (DQ003), missing client names (DQ004), stale pipeline deals (DQ005), won early stages (DQ006), value outliers (DQ007), negative receivables (DQ009), unbilled null values (DQ014), and cross-board unkeyed linkages (DQ015).
5. **Solid Test Coverage**:
   - 46 unit, integration, and golden evaluation tests passing cleanly with 100% success rate (`pytest backend/tests`).
6. **Production Cloud Infrastructure**:
   - Working deployment on Azure Container Apps (`skylark-bi-api`) and Azure Static Web Apps (`skylark-bi-frontend`).

---

## 4. Architecture Gaps

1. **Tool Catalog Completeness (Phase 2 & 4)**:
   - *Current State*: The tool registry implements 5 primary tools (`pipeline_summary`, `sector_performance`, `data_debt_ledger`, `revenue_ladder`, `unbilled_work_orders`).
   - *Required State*: The Master Prompt defines **14 canonical typed business tools**:
     1. `pipeline_summary`
     2. `revenue_waterfall` (renamed from `revenue_ladder` to match industry terminology)
     3. `sector_performance`
     4. `data_debt_ledger`
     5. `credit_risk`
     6. `aging_analysis`
     7. `client_concentration`
     8. `deal_slippage`
     9. `collection_efficiency`
     10. `margin_analysis`
     11. `conversion_velocity`
     12. `unbilled_exposure` (upgraded from `unbilled_work_orders`)
     13. `reconciliation_ledger`
     14. `cross_board_linkage` (explicit sector-level reconciliation with DQ015 warning).
2. **Dedicated Dashboard Endpoints (Phase 9 & Phase 32)**:
   - *Current State*: Analytics are computed on the fly through chat tool execution or individual tool REST endpoints.
   - *Required State*: Dedicated, fast REST endpoints are needed to serve the executive dashboards:
     - `GET /api/v1/dashboard/overview`
     - `GET /api/v1/dashboard/pipeline`
     - `GET /api/v1/dashboard/operations`
     - `GET /api/v1/dashboard/revenue`
     - `GET /api/v1/dashboard/data-quality`
3. **Structured BI Response Blocks**:
   - *Current State*: Orchestrator returns a structured payload with markdown answer, fact list, metrics, charts, and tables.
   - *Required State*: Must standardize on typed block objects: `insight`, `kpi_cards`, `evidence`, `data_quality`, `visual`, `table`, `next_questions`, and `trust_receipt`.

---

## 5. UX & Frontend Gaps

1. **Layout & Workspace Identity**:
   - *Current State*: `App.tsx` utilizes a generic two-tab toggle (`Agent` vs `Info`).
   - *Required State*: **Executive Intelligence Workspace** with a 3-column desktop layout:
     - **Left Navigation**: Overview, Pipeline, Operations, Revenue, Data Quality, and Agent Chat.
     - **Center Workspace**: Executive Conversation with rich BI blocks and empty-state Executive Command Center.
     - **Right Panel**: Live Workflow Execution graph, Evidence Ledger, Source Metadata, and Trust Receipt. Collapsible into a slide-over drawer on tablet/mobile screens.
2. **Data Visualizations**:
   - *Current State*: Basic SVG and simple Chart.js components.
   - *Required State*: Interactive Apache ECharts integration across the Executive Dashboards and chat inline responses (Funnel, Waterfall, Sector Sunburst/Bars, Aging Buckets).
3. **Question Chips & Suggestion Engine**:
   - *Current State*: Static starter buttons.
   - *Required State*: Dynamic, tool-validated suggestions categorized into `EXPLORE` (broad strategic queries) vs `INVESTIGATE` (deep drill-downs).

---

## 6. Data Access & Governance Gaps

1. **Cross-Board Linkage Rule Enforcement**:
   - *Current State*: Unkeyed cross-board join is flagged in DQ ledger as DQ015.
   - *Required State*: The `cross_board_linkage` tool must explicitly document `join_method: "sector_aggregation"` and emit the strict caveat: *"Direct item-level linkage unavailable; reconciled at sector level."*
2. **Cache & Invalidation Controls**:
   - Fast cache bust controls via API (`POST /api/v1/admin/cache/clear`) and visible source freshness indicator (`monday.com ● LIVE` vs `Snapshot Fallback`).

---

## 7. Agent & Orchestration Gaps

1. **Tool Invocation Versatility**:
   - Enable multi-tool parallel resolution for complex analytical questions (e.g., "Prepare a leadership update" calls `pipeline_summary`, `revenue_waterfall`, and `data_debt_ledger`).
2. **Fact Token Format Uniformity**:
   - Normalize support for both `[[F1]]` and `[F1]` fact tokens across all prompts and regex verifiers.
3. **Strict Zero Mental Math Enforcement**:
   - If an ungrounded number is detected, perform exactly 1 repair attempt; if it fails, immediately fall back to the deterministic, verified template.

---

## 8. Recommended Action Plan (Phases 2-14)

1. **Phase 2 & 3: Canonical 14 Business Tools**:
   - Implement all 14 tools in `backend/app/tools/` with typed inputs, DuckDB SQL execution, structured payloads, and row counts.
2. **Phase 4: FastMCP Server Alignment**:
   - Expose all 14 tools via FastMCP on `/mcp` with full parameter descriptions.
3. **Phase 5 & 6: Orchestrator & Verifier Hardening**:
   - Implement multi-tool synthesis, standardized BI block generation, and strict fact grounding.
4. **Phase 7: SSE Event Lifecycle**:
   - Stream granular events (`run.started`, `stage`, `tool`, `evidence`, `answer`, `run.finished`).
5. **Phase 8 & 9: Frontend 3-Column Rebuild & Executive Dashboards**:
   - Implement 3-column Executive Workspace in `frontend/src/` with navigation, conversation, intelligence panel, and ECharts-powered dashboards.
6. **Phase 10 & 11: Dynamic Chips & Trust Receipt**:
   - Build EXPLORE/INVESTIGATE chip engine and cryptographic trust receipt cards.
7. **Phase 12: Acceptance Verification**:
   - Verify Acceptance Tests 1, 2, and 3.
8. **Phase 13: Azure Cloud Deployment**:
   - Re-deploy backend container and frontend static assets.
9. **Phase 14: Documentation**:
   - Update `README.md`, `CLAUDE.md`, `DECISION_LOG.md`, and `docs/`.
