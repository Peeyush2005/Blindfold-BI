"""
Common normalization utilities, date parsing, fiscal year mapping,
and sector standardization.
"""

from typing import Tuple, Optional, Any
import pandas as pd
from datetime import datetime

DEFAULT_AS_OF_DATE = pd.Timestamp("2026-01-15")

CANONICAL_SECTORS = {
    "renewables": "Renewables",
    "powerline": "Powerline",
    "powerlines": "Powerline",
    "mining": "Mining",
    "infrastructure": "Infrastructure",
    "tender": "Tender",
    "gis": "GIS",
    "defence": "Defence",
    "forestry": "Forestry",
    "agriculture": "Agriculture",
    "urban planning": "Urban Planning",
    "water bodies": "Water Bodies",
}

ENERGY_SECTORS = ["Renewables", "Powerline"]


def clean_text(val: Any) -> Optional[str]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def normalize_sector(sector_raw: Optional[str]) -> str:
    if not sector_raw or pd.isna(sector_raw):
        return "Unspecified"
    s = str(sector_raw).strip()
    s_low = s.lower()
    return CANONICAL_SECTORS.get(s_low, s)


def get_indian_fy_and_quarter(dt: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Computes the Indian Fiscal Year and Quarter for a given date.
    Indian FY runs from April 1 to March 31.
    - Q1: April - June
    - Q2: July - September
    - Q3: October - December
    - Q4: January - March
    Example: 2026-01-15 -> ('FY25-26', 'Q4')
    """
    if pd.isna(dt):
        return None, None
    try:
        ts = pd.to_datetime(dt)
    except Exception:
        return None, None

    year = ts.year
    month = ts.month

    if month >= 4:
        fy = f"FY{str(year)[-2:]}-{str(year + 1)[-2:]}"
        quarter = f"Q{(month - 1) // 3}"
        # month 4-6 -> Q1, 7-9 -> Q2, 10-12 -> Q3
        quarter_map = {4: "Q1", 5: "Q1", 6: "Q1", 7: "Q2", 8: "Q2", 9: "Q2", 10: "Q3", 11: "Q3", 12: "Q3"}
        quarter = quarter_map[month]
    else:
        fy = f"FY{str(year - 1)[-2:]}-{str(year)[-2:]}"
        quarter = "Q4"

    return fy, quarter
