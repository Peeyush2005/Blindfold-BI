import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def clean_deals_data(file_path: Path) -> pd.DataFrame:
    """
    Cleans and standardizes the Deal funnel Data sheet.
    Removes header duplicate rows, handles missing numbers, and cleans dates and categories.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Deals file not found at: {file_path}")

    df = pd.read_excel(file_path, sheet_name="Deal tracker")

    # Filter header artifact repetitions
    df = df[df["Deal Stage"].astype(str).str.strip() != "Deal Stage"].copy()
    df = df[df["Deal Status"].astype(str).str.strip() != "Deal Status"].copy()
    df = df[df["Sector/service"].astype(str).str.strip() != "Sector/service"].copy()

    # Drop rows without deal name
    df = df.dropna(subset=["Deal Name"]).copy()
    df["Deal Name"] = df["Deal Name"].astype(str).str.strip()

    # Map & rename to clean snake_case
    rename_map = {
        "Deal Name": "deal_name",
        "Owner code": "owner_code",
        "Client Code": "client_code",
        "Deal Status": "deal_status",
        "Close Date (A)": "close_date",
        "Closure Probability": "closure_probability",
        "Masked Deal value": "deal_value",
        "Tentative Close Date": "tentative_close_date",
        "Deal Stage": "deal_stage",
        "Product deal": "product_deal",
        "Sector/service": "sector",
        "Created Date": "created_date"
    }
    df = df.rename(columns=rename_map)

    # Clean numeric fields
    df["deal_value"] = pd.to_numeric(df["deal_value"], errors="coerce").fillna(0.0)

    # Normalize categorical fields
    df["deal_status"] = df["deal_status"].fillna("Unknown").astype(str).str.strip()
    df["deal_stage"] = df["deal_stage"].fillna("Unknown").astype(str).str.strip()
    df["sector"] = df["sector"].fillna("Unspecified").astype(str).str.strip()
    df["closure_probability"] = df["closure_probability"].fillna("Unspecified").astype(str).str.strip()
    df["owner_code"] = df["owner_code"].fillna("UNASSIGNED").astype(str).str.strip()
    df["client_code"] = df["client_code"].fillna("UNKNOWN_CLIENT").astype(str).str.strip()
    df["product_deal"] = df["product_deal"].fillna("Unspecified").astype(str).str.strip()

    # Dates
    for date_col in ["close_date", "tentative_close_date", "created_date"]:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Add helper fields
    # Probability weight
    prob_weights = {"High": 0.8, "Medium": 0.5, "Low": 0.2}
    df["prob_weight"] = df["closure_probability"].map(prob_weights).fillna(0.3)
    df["weighted_deal_value"] = df["deal_value"] * df["prob_weight"]

    # Deal join key
    df["join_key"] = df["deal_name"].str.lower().str.strip()

    return df

def clean_work_orders_data(file_path: Path) -> pd.DataFrame:
    """
    Cleans and standardizes the Work Order Tracker sheet.
    Row 0 in Excel is blank, row 1 contains headers.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Work order file not found at: {file_path}")

    # Row 0 is blank, row 1 has headers (skiprows=1)
    df = pd.read_excel(file_path, sheet_name="work order tracker", skiprows=1)

    # Drop rows without deal name masked
    df = df.dropna(subset=["Deal name masked"]).copy()
    df["Deal name masked"] = df["Deal name masked"].astype(str).str.strip()

    # Rename key columns to snake_case
    rename_map = {
        "Deal name masked": "deal_name",
        "Customer Name Code": "client_code",
        "Serial #": "serial_no",
        "Nature of Work": "nature_of_work",
        "Last executed month of recurring project": "last_executed_month",
        "Execution Status": "execution_status",
        "Data Delivery Date": "data_delivery_date",
        "Date of PO/LOI": "po_date",
        "Document Type": "document_type",
        "Probable Start Date": "start_date",
        "Probable End Date": "end_date",
        "BD/KAM Personnel code": "owner_code",
        "Sector": "sector",
        "Type of Work": "type_of_work",
        "Is any Skylark software platform part of the client deliverables in this deal?": "has_software",
        "Last invoice date": "last_invoice_date",
        "latest invoice no.": "latest_invoice_no",
        "Amount in Rupees (Excl of GST) (Masked)": "amount_excl_gst",
        "Amount in Rupees (Incl of GST) (Masked)": "amount_incl_gst",
        "Billed Value in Rupees (Excl of GST.) (Masked)": "billed_excl_gst",
        "Billed Value in Rupees (Incl of GST.) (Masked)": "billed_incl_gst",
        "Collected Amount in Rupees (Incl of GST.) (Masked)": "collected_incl_gst",
        "Amount to be billed in Rs. (Exl. of GST) (Masked)": "to_be_billed_excl_gst",
        "Amount to be billed in Rs. (Incl. of GST) (Masked)": "to_be_billed_incl_gst",
        "Amount Receivable (Masked)": "receivable_amount",
        "AR Priority account": "ar_priority",
        "Quantity by Ops": "quantity_ops",
        "Quantities as per PO": "quantity_po",
        "Quantity billed (till date)": "quantity_billed",
        "Balance in quantity": "quantity_balance",
        "Invoice Status": "invoice_status",
        "Expected Billing Month": "expected_billing_month",
        "Actual Billing Month": "actual_billing_month",
        "Actual Collection Month": "actual_collection_month",
        "WO Status (billed)": "wo_status_billed",
        "Collection status": "collection_status",
        "Collection Date": "collection_date",
        "Billing Status": "billing_status"
    }
    df = df.rename(columns=rename_map)

    # Clean numeric fields
    numeric_cols = [
        "amount_excl_gst", "amount_incl_gst",
        "billed_excl_gst", "billed_incl_gst",
        "collected_incl_gst",
        "to_be_billed_excl_gst", "to_be_billed_incl_gst",
        "receivable_amount"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Standardize string/categorical columns
    df["execution_status"] = df["execution_status"].fillna("Unknown").astype(str).str.strip()
    df["execution_status"] = df["execution_status"].replace({
        "Pause / struck": "Paused/Stuck",
        "Executed until current month": "Ongoing (Monthly)"
    })

    # Clean billing status (fix typo "BIlled" -> "Billed")
    df["billing_status"] = df["billing_status"].fillna("Not Specified").astype(str).str.strip()
    df["billing_status"] = df["billing_status"].replace({"BIlled": "Billed"})

    df["sector"] = df["sector"].fillna("Unspecified").astype(str).str.strip()
    df["owner_code"] = df["owner_code"].fillna("UNASSIGNED").astype(str).str.strip()
    df["client_code"] = df["client_code"].fillna("UNKNOWN_CLIENT").astype(str).str.strip()

    # Dates
    date_cols = ["data_delivery_date", "po_date", "start_date", "end_date", "last_invoice_date", "collection_date"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Join key
    df["join_key"] = df["deal_name"].str.lower().str.strip()

    return df
