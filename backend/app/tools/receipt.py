"""
Trust Receipt Generator for Blindfold BI.
Attaches cryptographic audit provenance, deterministic confidence scoring,
and execution timings to tool calls (Section 5.4).
"""

import hashlib
from typing import Dict, Any, List, Optional, Literal
from datetime import date

from app.contracts import (
    Receipt,
    SnapshotInfo,
    CallInfo,
    RowAccounting,
    contract_manager,
)
from app.data.normalize.common import DEFAULT_AS_OF_DATE


def calculate_confidence(
    considered: int,
    used: int,
    missing_key_field: int = 0,
    is_snapshot_stale: bool = False,
    single_entity_share_pct: float = 0.0,
    cross_board_link_coverage_pct: Optional[float] = None,
    verifier_fallback: bool = False,
) -> tuple[Literal["high", "medium", "low"], List[str]]:
    """
    Deterministic confidence calculation:
    - Starts HIGH.
    - Drops to MEDIUM if:
      * > 20% of rows needed are excluded or missing key field
      * snapshot is stale
    - Drops to LOW if:
      * > 50% of rows are excluded
      * one entity holds > 50% of value
      * cross-board link coverage is < 50%
      * verifier fell back to template after failures
    """
    reasons: List[str] = []
    level: Literal["high", "medium", "low"] = "high"

    excluded_ratio = (considered - used) / considered if considered > 0 else 0.0
    missing_ratio = missing_key_field / considered if considered > 0 else 0.0

    # Low checks
    if excluded_ratio > 0.50:
        level = "low"
        reasons.append(f">50% of candidate records excluded ({excluded_ratio*100:.1f}%)")
    if single_entity_share_pct > 50.0:
        level = "low"
        reasons.append(f"Single entity concentration exceeds 50% ({single_entity_share_pct:.1f}%)")
    if cross_board_link_coverage_pct is not None and cross_board_link_coverage_pct < 50.0:
        level = "low"
        reasons.append(f"Cross-board linkage feasibility under 50% ({cross_board_link_coverage_pct:.1f}%)")
    if verifier_fallback:
        level = "low"
        reasons.append("Verifier fallback to deterministic template invoked")

    if level == "low":
        return level, reasons

    # Medium checks
    if excluded_ratio > 0.20 or missing_ratio > 0.20:
        level = "medium"
        reasons.append("Over 20% of records excluded or missing analytical fields")
    if is_snapshot_stale:
        level = "medium"
        reasons.append("Underlying data snapshot exceeds TTL freshness threshold")

    return level, reasons


def make_trust_receipt(
    tool_name: str,
    sql_executed: str,
    duration_ms: float,
    row_count: int,
    params: Optional[List[Any]] = None,
    as_of_date: Optional[str] = None,
    considered: Optional[int] = None,
    used: Optional[int] = None,
    caveats: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generates deterministic trust receipt with query hash and metadata.
    """
    hasher = hashlib.sha256()
    hasher.update(tool_name.encode("utf-8"))
    hasher.update(sql_executed.encode("utf-8"))
    if params:
        hasher.update(str(params).encode("utf-8"))
    query_hash = hasher.hexdigest()[:16]

    cons = considered if considered is not None else row_count
    usd = used if used is not None else row_count
    conf_level, reasons = calculate_confidence(considered=cons, used=usd)

    return {
        "tool_name": tool_name,
        "query_hash": query_hash,
        "execution_ms": round(duration_ms, 2),
        "duration_ms": round(duration_ms, 2),
        "row_count": row_count,
        "as_of_date": as_of_date or DEFAULT_AS_OF_DATE.strftime("%Y-%m-%d"),
        "sql_executed": sql_executed.strip(),
        "deterministic": True,
        "confidence": conf_level,
        "confidence_reasons": reasons,
        "caveats": caveats or [],
    }
