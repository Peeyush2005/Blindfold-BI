# Blindfold BI Data Profiling Notes & Verified Findings

Generated automatically on 2026-09-19 23:39:12 by `scripts/profile_data.py`.

## 1. Ground Truth Spot Check Summary (Section 3.6)

| Ground Truth Anchor | Expected | Actual Profiling Result | Status |
|---|---|---|---|
| Deals after header + duplicate cleanup | 332 | 332 | MATCH |
| Open deals / known value / value sum | 49 / 47 / ₹68.82 Cr | 49 / 47 / ₹68.82 Cr | MATCH |
| Tender share of open pipeline | 77.3% (₹53.20 Cr) | 77.3% (₹53.2 Cr) | MATCH |
| Open pipeline excluding Tender | ₹15.62 Cr | ₹15.62 Cr | MATCH |
| Open energy (Renewables + Powerline) | 12 deals, ₹3.19 Cr | 12 deals, ₹3.19 Cr | MATCH |
| Won deals with known value | 64 of 153 (₹9.50 Cr) | 64 of 153 (₹9.5 Cr) | MATCH |
| Work orders / total contract excl GST | 176 / ₹21.16 Cr | 176 / ₹21.16 Cr | MATCH |
| Total receivable | ₹3.63 Cr (11 negative rows) | ₹3.63 Cr (11 negative rows) | MATCH |
| Fully empty WO columns | 4 | 4 (Expected Billing Month, Actual Collection Month, Collection status, Collection Date) | MATCH |

## 2. Deals Sheet In-Depth Metrics

- **Raw Rows:** 346
- **Stray Header Rows Dropped (DQ001):** 2
- **Exact Duplicate Rows Dropped (DQ002):** 12
- **Net Cleaned Deals Rows:** 332
- **Status Breakdown:** {'Won': 153, 'Dead': 127, 'Open': 49, 'On Hold': 2, nan: 1}
- **Won Stage Anomaly (DQ006):** 61 Won deals still marked as stage 'A. Lead Generated'. Status is authoritative.
- **Stale Open Deals (DQ005):** 8 open deals have a tentative close date before the as-of date (2026-01-15).

## 3. Work Orders Sheet In-Depth Metrics

- **Raw Rows:** 176 (Header at index 1 - 2nd line of spreadsheet)
- **Empty Columns Dropped (DQ008):** ['Expected Billing Month', 'Actual Collection Month', 'Collection status', 'Collection Date']
- **Total Contract Value (Excl. GST):** ₹21.16 Cr
- **Total Receivable:** ₹3.63 Cr (11 credit/overbilling entries)
- **Billed Excl. GST Nulls (DQ014):** 63 rows where null strictly indicates unbilled.
- **Collected Amount Nulls:** 98 rows.
- **Execution Status Breakdown:** {'Completed': 117, 'Ongoing': 25, 'Executed until current month': 12, 'Not Started': 11, 'Pause / struck': 4, nan: 4, 'Partial Completed': 2, 'Details pending from Client': 1}
- **Completed WO Missing Delivery Date:** 62 rows.

## 4. Cross-Board Linkage Findings

- `Deal Name` (Deals) vs `Deal name masked` (Work Orders): Independently masked aliases. Matching produces 0 true joins; alias collisions lead to false linkages.
- Client Code range mismatch: Work Orders clients are bounded 1-52, whereas Deals clients span 1-200. Client ID overlap is statistically random.
- **Strict Architecture Rule:** Sector is the only reliable common dimension. Cross-board intelligence aggregates strictly by canonical sector.
