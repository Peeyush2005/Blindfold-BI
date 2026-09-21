# Architectural Decision Log: Blindfold BI

This document records the architectural decisions, trade-offs, and governance policies governing the Blindfold BI platform for Skylark Drones.

---

## 1. Two-Tab UI (Agent | Info) vs. Multi-Page Dashboards

- **Context**: The original implementation exposed traditional dashboard views, pipeline simulators with manual playback dials, and navigation routers. In practice, fixed dashboards create maintenance overhead and encourage static reporting, but a completely single screen hides context a user needs to trust and audit the agent.
- **Decision**: Redesign the interface into exactly two tabs (`Agent` and `Info`), preserving conversation state between tabs:
  - Header with product title, segmented control `Agent | Info`, live monday.com source badge (`monday.com · synced HH:MM · as of 15 Jan 2026`, or `Stale snapshot` / `Not connected`), and light/dark theme toggle.
  - `Agent` tab: Centered 760px conversation column, empty state with 4 grouped starter chip categories, question-driven answers with dynamic BI blocks (`text`, `kpi`, `chart`, `table`), trust badge, inline assumptions, follow-up chips, and collapsible Run panel.
  - `Info` tab: Transparency center with 6 live API-fetched sections (Data source & freshness, Data health summary with "Ask the agent" links, Definitions & assumptions, What you can ask with clickable tool chips, Privacy & limits, API links and `/healthz`/`/readyz` probes).
- **Trade-off**: BI visuals (KPI cards, charts, tables) still appear exclusively inside agent answers; the Info tab holds reference information, not a static dashboard.

---

## 2. Deterministic Analytical Tools Engine vs. LLM Text-to-SQL

- **Context**: LLMs performing Text-to-SQL or in-context mental math exhibit nondeterministic calculation drift, arithmetic errors on large Indian Rupee denominations (`Crore`/`Lakh`), and vulnerability to SQL injection or ungrounded table joins.
- **Decision**: Implement a pure in-process DuckDB analytical tools engine (`backend/app/tools/`). The LLM never writes raw SQL queries and never computes numbers.
  - Metric calculations are bound to pre-compiled, parameter-sanitized SQL templates.
  - Indian Financial Year definitions are strictly enforced (FY starts April 1; Q4 FY25-26 corresponds to Jan 1, 2026 – Mar 31, 2026, with an as-of date of 15 Jan 2026).
  - Energy sector aggregation consolidates canonical labels present in the dataset: `Renewables` and `Powerline` (reflecting actual green energy and transmission asset vertical classifications; `Power` and `Utilities` do not exist in the source CRM data).
- **Trade-off**: The platform only answers analytical questions mapped to registered tools. New analytical dimensions require registering new typed tool schemas rather than unbounded free-form querying.

---

## 3. Numbers-by-Reference Protocol with Claim-Only Verification and Repair Loops

- **Context**: Even when provided with correct facts, generative language models frequently misquote numbers, transpose digits, or hallucinate external statistics during natural language synthesis. Overly aggressive verifiers that reject every isolated digit also reject legitimate non-claim labels (such as `Q4`, `FY25-26`, ordinals like `1st`, or `top 3`), triggering unnecessary fallbacks to static templates.
- **Decision**: Narration uses a claim-only numbers-by-reference protocol (`[[F#]]` tokens) with automated repair before fallback.
  - The synthesis prompt supplies only pseudonymized tool outputs and a fact dictionary (`F1: 49`, `F2: ₹68.82 Cr`) with explicit fact roles (`primary`, `support`, `caveat`).
  - The model outputs narrative prose containing reference tokens rather than raw quantitative claims.
  - **Claim-Only Verifier**: Rejects ungrounded quantitative claims (currency amounts `₹...`, percentages `...%`, counts `... deals`, ratios), while explicitly allowing valid structural labels (`Q1`–`Q4`, fiscal periods `FY25-26`, ordinals `1st`/`2nd`, intent limits like `top 3`, and verified dates).
  - **Single Repair Loop**: On verifier failure, the orchestrator issues exactly one repair call highlighting the exact offending spans. Only if the repaired draft fails verification does it fall back to question-aware dynamic templates.
- **Trade-off**: Incurs an additional LLM turn (~400–600ms) when a draft requires repair, but slashes template fallback rates below 10% while guaranteeing zero hallucinated claims.

---

## 4. Real-Time Asynchronous SSE Streaming vs. Stored Trace Playback

- **Context**: Previous mock simulators replayed pre-recorded or batched execution traces, misleading users regarding real-time system state and degrading visibility into long-running operations.
- **Decision**: Orchestrate execution across an asynchronous queue (`asyncio.Queue`) emitting Server-Sent Events (`text/event-stream`) in real time.
  - HTTP headers enforce streaming: `Cache-Control: no-cache`, `X-Accel-Buffering: no`, with 15-second keepalive pings (`: keepalive\n\n`).
  - Stage events (`run.started`, `stage`, `tool`, `llm`, `answer`, `run.finished`/`run.error`) emit at the actual instant each operation starts and finishes.
  - Client-side state machine moves stages from `queued` to `running` to `done`/`warn`/`error` organically.
- **Trade-off**: Requires persistent HTTP streaming connections and client-side reconnection logic.

---

## 5. Strict Read-Only monday.com Data Governance

- **Context**: Connecting operational business tools directly to core enterprise CRM/Work OS boards risks accidental data overwrites or unauthorized status mutations.
- **Decision**: Enforce strict read-only access to monday.com boards.
  - The backend only issues GraphQL read queries (`boards`, `items_page`).
  - Any GraphQL `mutation` is strictly forbidden and rejected by a `MutationForbiddenError`.
  - Continuous integration enforces zero occurrences of `mutation` in `backend/app/`.
  - All dataset snapshots are cached in memory with a 10-minute TTL and single-flight background refresh.
- **Trade-off**: Eliminates 2-way alert posting to monday.com items; diagnostic alerts and data debt findings remain inside the BI platform.

---

## 6. Blindfold Privacy Gateway: HMAC-Salted Surrogate Tokenization

- **Context**: Enterprise commercial pipeline data contains sensitive counterparty names, executive contacts, and project deal codenames. Transmitting raw entity identifiers to public LLM inference endpoints violates confidentiality agreements.
- **Decision**: Route all inputs and outputs through the Blindfold Privacy Gateway.
  - Entities are matched via case-insensitive regex and substituted with session-scoped HMAC-SHA256 surrogate tokens (`CLIENT_001`, `DEAL_002`) prior to external model transit.
  - The session vault maintains bidirectional mappings in memory.
  - Re-identification occurs strictly server-side post-verification prior to client transmission.
- **Trade-off**: Minor tokenization overhead during the `understand` and `finalize` stages (~15ms). Prevents external models from retaining proprietary organizational entities.

---

## 7. Cross-Board Join Refusal (DQ015) vs. Synthetic Fuzzy Merging

- **Context**: The `Deal funnel` and `Work_Order_Tracker` boards lack a shared foreign key or standard order ID. Attempting naive fuzzy name joins produces false commercial-to-operational conversions.
- **Decision**: Explicitly refuse direct item-level joins between deals and work orders, formally logging audit check `DQ015`. Reconcile cross-board activity exclusively at the sector level across 9 canonical sectors.
- **Trade-off**: The platform refuses queries requesting direct line-item deal-to-work-order linkages, transparently reporting the lack of a shared primary key.
