# Blindfold BI: monday.com Business-Intelligence Agent (Skylark Drones Assignment)

## Core Principles & Guidelines
1. **The model never touches data**: It receives only tool schemas and pseudonymized tool results. All arithmetic is computed deterministically in DuckDB with zero LLM mental math.
2. **Numbers-by-reference**: The narrator generates prose with placeholders like `[[F1]]`; the server verifies and substitutes verified values.
3. **Decentralized Function Calling**: Every capability is an independent typed tool behind a registry that can run inproc, over REST (`/api/tools/{name}`), or over MCP (`/mcp`).
4. **Blindfold Gateway**: Entity identifiers (`client_id`, `owner_id`, `deal_alias`) are tokenized with session-scoped HMAC salts before prompts reach any LLM, and rehydrated server-side after verification.
5. **Contract-driven Ground Truth**: Versioned YAML contracts in `contract/` define metrics, sectors, periods, stages, ambiguities, and schema mappings.
6. **Data Resilience & DQ Ledger**: Handles stray headers (DQ001), duplicates (DQ002), null deal values (DQ003), missing entities (DQ004), stale pipeline (DQ005), won early stages (DQ006), outliers (DQ007), empty columns (DQ008), negative receivables (DQ009), unbilled nulls (DQ014), unkeyed cross-board linkage (DQ015).
7. **Read-only Monday.com Guard**: No GraphQL `mutation` is permitted. Unit tests enforce zero mutations in `backend/app`.
8. **Visible Pipeline Simulation**: Live workflow graph emits SSE run events for S1 Intake -> S2 Understand -> S3 Plan -> S4 Blindfold-in -> S5 Tools -> S6 Blindfold-out -> S7 Narrate -> S8 Verify -> S9 Re-identify -> S10 Render.
9. **Never Invent Data**: Profile datasets with `scripts/profile_data.py`. Ground truths must match section 3.6.
