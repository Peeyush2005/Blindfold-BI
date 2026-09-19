#!/usr/bin/env python3
"""
scripts/profile_data.py
Profiles the Deals and Work Orders datasets, computes all data quality metrics,
validates against the section 3.6 ground truth anchors, and writes docs/DATA_NOTES.md.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS_PATH = os.path.join(ROOT_DIR, "Deal funnel Data.xlsx")
WO_PATH = os.path.join(ROOT_DIR, "Work_Order_Tracker Data.xlsx")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
DATA_NOTES_PATH = os.path.join(DOCS_DIR, "DATA_NOTES.md")

os.makedirs(DOCS_DIR, exist_ok=True)


def profile_deals():
    df_raw = pd.read_excel(DEALS_PATH)
    raw_row_count = len(df_raw)

    # 1. Identify stray repeated header rows (e.g. Deal Status == "Deal Status")
    status_col_name = next((c for c in df_raw.columns if "status" in str(c).lower()), "Deal Status")
    stray_header_mask = df_raw[status_col_name].astype(str).str.strip().str.lower() == status_col_name.strip().lower()
    stray_headers = df_raw[stray_header_mask]
    stray_header_count = len(stray_headers)

    df_no_headers = df_raw[~stray_header_mask].copy()
    row_count_after_header_drop = len(df_no_headers)

    # 2. Exact duplicate rows
    duplicate_mask = df_no_headers.duplicated()
    duplicates = df_no_headers[duplicate_mask]
    duplicate_count = len(duplicates)

    df_clean = df_no_headers.drop_duplicates().copy()
    cleaned_row_count = len(df_clean)

    # Standardize column names
    col_map = {
        "Deal Name": "deal_alias",
        "Owner code": "owner_id",
        "Client Code": "client_id",
        "Deal Status": "status",
        "Close Date (A)": "close_date_actual",
        "Closure Probability": "closure_probability",
        "Masked Deal value": "deal_value",
        "Tentative Close Date": "tentative_close_date",
        "Deal Stage": "stage_raw",
        "Product deal": "product",
        "Sector/service": "sector",
        "Created Date": "created_date",
    }
    df_clean.rename(columns=col_map, inplace=True)

    # Coerce deal_value to numeric
    df_clean["deal_value"] = pd.to_numeric(df_clean["deal_value"], errors="coerce")

    # Status counts
    status_counts = df_clean["status"].value_counts(dropna=False).to_dict()

    # Open deals
    open_deals = df_clean[df_clean["status"] == "Open"]
    open_count = len(open_deals)
    open_with_value = open_deals[open_deals["deal_value"].notna()]
    open_known_value_count = len(open_with_value)
    open_known_value_sum = open_with_value["deal_value"].sum()

    # Tender outlier analysis
    tender_open = open_deals[open_deals["sector"] == "Tender"]
    tender_open_count = len(tender_open)
    tender_open_value = tender_open["deal_value"].sum()
    tender_share_pct = (tender_open_value / open_known_value_sum) * 100 if open_known_value_sum else 0
    open_excl_tender_value = open_known_value_sum - tender_open_value

    # Largest tender deal
    max_deal = open_deals.loc[open_deals["deal_value"].idxmax()] if open_known_value_count else None

    # Won deals
    won_deals = df_clean[df_clean["status"] == "Won"]
    won_count = len(won_deals)
    won_with_value = won_deals[won_deals["deal_value"].notna()]
    won_known_value_count = len(won_with_value)
    won_known_value_sum = won_with_value["deal_value"].sum()

    # Won deals with early stage "A. Lead Generated"
    won_stage_a = won_deals[won_deals["stage_raw"].astype(str).str.contains("A. Lead Generated|A.", regex=True, na=False)]
    won_stage_a_count = len(won_stage_a)

    # Energy sector deals (Renewables + Powerline)
    energy_open = open_deals[open_deals["sector"].isin(["Renewables", "Powerline"])]
    energy_open_count = len(energy_open)
    energy_open_value = energy_open["deal_value"].sum()

    # Stale open deals (tentative_close_date < 2026-01-15)
    as_of_date = pd.Timestamp("2026-01-15")
    open_tentative_dates = pd.to_datetime(open_deals["tentative_close_date"], errors="coerce")
    stale_open_deals = open_deals[open_tentative_dates < as_of_date]
    stale_open_count = len(stale_open_deals)

    return {
        "raw_rows": raw_row_count,
        "stray_headers": stray_header_count,
        "rows_after_headers": row_count_after_header_drop,
        "duplicates": duplicate_count,
        "cleaned_rows": cleaned_row_count,
        "status_counts": status_counts,
        "open_count": open_count,
        "open_known_value_count": open_known_value_count,
        "open_known_value_sum": open_known_value_sum,
        "tender_open_count": tender_open_count,
        "tender_open_value": tender_open_value,
        "tender_share_pct": tender_share_pct,
        "open_excl_tender_value": open_excl_tender_value,
        "won_count": won_count,
        "won_known_value_count": won_known_value_count,
        "won_known_value_sum": won_known_value_sum,
        "won_stage_a_count": won_stage_a_count,
        "energy_open_count": energy_open_count,
        "energy_open_value": energy_open_value,
        "stale_open_count": stale_open_count,
        "max_deal_value": max_deal["deal_value"] if max_deal is not None else 0,
        "max_deal_alias": max_deal["deal_alias"] if max_deal is not None else "",
    }


def profile_work_orders():
    # Work Orders has row 1 blank or header on row 2
    # Find header by scanning first 5 rows
    df_preview = pd.read_excel(WO_PATH, header=None, nrows=5)
    header_idx = None
    for idx, row in df_preview.iterrows():
        row_str = " ".join([str(x).lower() for x in row.dropna()])
        if "deal name" in row_str or "contract value" in row_str or "work order" in row_str or "invoice" in row_str:
            header_idx = idx
            break

    if header_idx is None:
        header_idx = 1 # Row 2 in 1-based index is index 1

    df = pd.read_excel(WO_PATH, header=header_idx)
    raw_row_count = len(df)

    # Strip column names
    df.columns = [str(c).strip() for c in df.columns]

    # 4 columns 100% empty
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    empty_cols_count = len(empty_cols)

    # Find contract value excl GST
    # Matches 'Amount in Rupees (Excl of GST) (Masked)' or variations
    contract_col = None
    for c in df.columns:
        c_low = c.lower()
        if ("amount in rupees" in c_low or "contract value" in c_low) and "excl" in c_low:
            contract_col = c
            break

    total_contract_value = pd.to_numeric(df[contract_col], errors="coerce").sum() if contract_col else 0

    # Find amount receivable
    receivable_col = None
    for c in df.columns:
        if "receivable" in c.lower():
            receivable_col = c
            break

    rec_series = pd.to_numeric(df[receivable_col], errors="coerce") if receivable_col else pd.Series([], dtype=float)
    total_receivable = rec_series.sum()
    negative_receivable_count = (rec_series < 0).sum()

    # Billed excl vs incl GST
    billed_excl_col = next((c for c in df.columns if "billed" in c.lower() and "excl" in c.lower()), None)
    billed_incl_col = next((c for c in df.columns if "billed" in c.lower() and "incl" in c.lower()), None)

    billed_excl_null_count = df[billed_excl_col].isna().sum() if billed_excl_col else 0

    # Collected amount
    collected_col = next((c for c in df.columns if "collected" in c.lower() and "amount" in c.lower()), None)
    collected_null_count = df[collected_col].isna().sum() if collected_col else 0

    # Execution status counts
    exec_col = next((c for c in df.columns if "execution" in c.lower() and "status" in c.lower()), None)
    exec_status_counts = df[exec_col].value_counts(dropna=False).to_dict() if exec_col else {}

    # Data delivery date missing for completed
    delivery_col = next((c for c in df.columns if "delivery" in c.lower()), None)
    completed_missing_delivery = 0
    if exec_col and delivery_col:
        completed = df[df[exec_col] == "Completed"]
        completed_missing_delivery = completed[delivery_col].isna().sum()

    return {
        "raw_rows": raw_row_count,
        "header_row_index": header_idx,
        "empty_cols": empty_cols,
        "empty_cols_count": empty_cols_count,
        "total_contract_value": total_contract_value,
        "total_receivable": total_receivable,
        "negative_receivable_count": negative_receivable_count,
        "billed_excl_null_count": billed_excl_null_count,
        "collected_null_count": collected_null_count,
        "exec_status_counts": exec_status_counts,
        "completed_missing_delivery": completed_missing_delivery,
    }


def main():
    print("=" * 70)
    print("BLINDFOLD BI DATA PROFILING SCRIPT (Phase 0)")
    print("=" * 70)

    deals = profile_deals()
    wo = profile_work_orders()

    # Section 3.6 Validation Checks
    checks = [
        ("Deals after header+duplicate cleanup", deals["cleaned_rows"], 332),
        ("Open deals count", deals["open_count"], 49),
        ("Open deals with known value", deals["open_known_value_count"], 47),
        ("Known open value (Cr)", round(deals["open_known_value_sum"] / 1e7, 2), 68.82),
        ("Tender share of open pipeline (%)", round(deals["tender_share_pct"], 1), 77.3),
        ("Open pipeline excluding Tender (Cr)", round(deals["open_excl_tender_value"] / 1e7, 2), 15.62),
        ("Open energy deals count", deals["energy_open_count"], 12),
        ("Open energy value (Cr)", round(deals["energy_open_value"] / 1e7, 2), 3.19),
        ("Won deals count", deals["won_count"], 153),
        ("Won deals with known value", deals["won_known_value_count"], 64),
        ("Won known value (Cr)", round(deals["won_known_value_sum"] / 1e7, 2), 9.50),
        ("Work orders count", wo["raw_rows"], 176),
        ("WO contract value excl GST (Cr)", round(wo["total_contract_value"] / 1e7, 2), 21.16),
        ("WO total receivable (Cr)", round(wo["total_receivable"] / 1e7, 2), 3.63),
        ("Negative receivables count", wo["negative_receivable_count"], 11),
        ("Fully empty WO columns", wo["empty_cols_count"], 4),
    ]

    all_passed = True
    print("\n--- GROUND TRUTH SPOT CHECKS (Section 3.6) ---")
    for name, actual, expected in checks:
        passed = (actual == expected)
        if not passed:
            all_passed = False
        status = "PASSED" if passed else "FAILED"
        print(f"[{status}] {name:40s} Actual: {str(actual):>8s} | Expected: {str(expected):>8s}")

    print("\nOverall Spot Checks Status:", "ALL PASSED (100% Match)" if all_passed else "MISMATCH FOUND")

    # Generate docs/DATA_NOTES.md
    markdown = f"""# Blindfold BI Data Profiling Notes & Verified Findings

Generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by `scripts/profile_data.py`.

## 1. Ground Truth Spot Check Summary (Section 3.6)

| Ground Truth Anchor | Expected | Actual Profiling Result | Status |
|---|---|---|---|
| Deals after header + duplicate cleanup | 332 | {deals['cleaned_rows']} | {'MATCH' if deals['cleaned_rows'] == 332 else 'DIFF'} |
| Open deals / known value / value sum | 49 / 47 / ₹68.82 Cr | {deals['open_count']} / {deals['open_known_value_count']} / ₹{round(deals['open_known_value_sum']/1e7, 2)} Cr | {'MATCH' if deals['open_count'] == 49 and round(deals['open_known_value_sum']/1e7, 2) == 68.82 else 'DIFF'} |
| Tender share of open pipeline | 77.3% (₹53.20 Cr) | {round(deals['tender_share_pct'], 1)}% (₹{round(deals['tender_open_value']/1e7, 2)} Cr) | {'MATCH' if round(deals['tender_share_pct'], 1) == 77.3 else 'DIFF'} |
| Open pipeline excluding Tender | ₹15.62 Cr | ₹{round(deals['open_excl_tender_value']/1e7, 2)} Cr | {'MATCH' if round(deals['open_excl_tender_value']/1e7, 2) == 15.62 else 'DIFF'} |
| Open energy (Renewables + Powerline) | 12 deals, ₹3.19 Cr | {deals['energy_open_count']} deals, ₹{round(deals['energy_open_value']/1e7, 2)} Cr | {'MATCH' if deals['energy_open_count'] == 12 and round(deals['energy_open_value']/1e7, 2) == 3.19 else 'DIFF'} |
| Won deals with known value | 64 of 153 (₹9.50 Cr) | {deals['won_known_value_count']} of {deals['won_count']} (₹{round(deals['won_known_value_sum']/1e7, 2)} Cr) | {'MATCH' if deals['won_known_value_count'] == 64 and deals['won_count'] == 153 else 'DIFF'} |
| Work orders / total contract excl GST | 176 / ₹21.16 Cr | {wo['raw_rows']} / ₹{round(wo['total_contract_value']/1e7, 2)} Cr | {'MATCH' if wo['raw_rows'] == 176 and round(wo['total_contract_value']/1e7, 2) == 21.16 else 'DIFF'} |
| Total receivable | ₹3.63 Cr (11 negative rows) | ₹{round(wo['total_receivable']/1e7, 2)} Cr ({wo['negative_receivable_count']} negative rows) | {'MATCH' if round(wo['total_receivable']/1e7, 2) == 3.63 and wo['negative_receivable_count'] == 11 else 'DIFF'} |
| Fully empty WO columns | 4 | {wo['empty_cols_count']} ({', '.join(wo['empty_cols'])}) | {'MATCH' if wo['empty_cols_count'] == 4 else 'DIFF'} |

## 2. Deals Sheet In-Depth Metrics

- **Raw Rows:** {deals['raw_rows']}
- **Stray Header Rows Dropped (DQ001):** {deals['stray_headers']}
- **Exact Duplicate Rows Dropped (DQ002):** {deals['duplicates']}
- **Net Cleaned Deals Rows:** {deals['cleaned_rows']}
- **Status Breakdown:** {deals['status_counts']}
- **Won Stage Anomaly (DQ006):** {deals['won_stage_a_count']} Won deals still marked as stage 'A. Lead Generated'. Status is authoritative.
- **Stale Open Deals (DQ005):** {deals['stale_open_count']} open deals have a tentative close date before the as-of date (2026-01-15).

## 3. Work Orders Sheet In-Depth Metrics

- **Raw Rows:** {wo['raw_rows']} (Header at index {wo['header_row_index']} - 2nd line of spreadsheet)
- **Empty Columns Dropped (DQ008):** {wo['empty_cols']}
- **Total Contract Value (Excl. GST):** ₹{round(wo['total_contract_value']/1e7, 2)} Cr
- **Total Receivable:** ₹{round(wo['total_receivable']/1e7, 2)} Cr ({wo['negative_receivable_count']} credit/overbilling entries)
- **Billed Excl. GST Nulls (DQ014):** {wo['billed_excl_null_count']} rows where null strictly indicates unbilled.
- **Collected Amount Nulls:** {wo['collected_null_count']} rows.
- **Execution Status Breakdown:** {wo['exec_status_counts']}
- **Completed WO Missing Delivery Date:** {wo['completed_missing_delivery']} rows.

## 4. Cross-Board Linkage Findings

- `Deal Name` (Deals) vs `Deal name masked` (Work Orders): Independently masked aliases. Matching produces 0 true joins; alias collisions lead to false linkages.
- Client Code range mismatch: Work Orders clients are bounded 1-52, whereas Deals clients span 1-200. Client ID overlap is statistically random.
- **Strict Architecture Rule:** Sector is the only reliable common dimension. Cross-board intelligence aggregates strictly by canonical sector.
"""
    with open(DATA_NOTES_PATH, "w") as f:
        f.write(markdown)

    print(f"\nSuccessfully wrote profile findings to: {DATA_NOTES_PATH}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
