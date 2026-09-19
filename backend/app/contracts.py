"""
Canonical Pydantic contracts and YAML loader for Blindfold BI.
Enforces Section 5.4 specifications and mirrors TypeScript types.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Literal, Union
from datetime import date
import yaml
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Core Pydantic Contracts (Section 5.4)
# -------------------------------------------------------------------------

class Fact(BaseModel):
    id: str                                                 # e.g. "F1", "F2"
    metric: str                                             # contract metric key, e.g. "open_pipeline_value"
    label: str                                              # Human readable label
    value: Union[bool, float, int, str, None]
    unit: Literal["INR", "count", "pct", "days", "ratio", "text"]
    display: str                                            # "₹68.82 Cr", "49 deals", "77.3%"
    dimensions: Dict[str, str] = Field(default_factory=dict)# {"sector": "Energy", "period": "Q4 FY25-26"}
    n: Optional[int] = None                                 # rows used
    n_missing: Optional[int] = None                         # rows lacking the needed field
    caveat_codes: List[str] = Field(default_factory=list)   # DQ codes touching this fact (e.g. ["DQ007"])
    must_mention: bool = False


class Table(BaseModel):
    id: str
    title: str
    headers: List[str]
    rows: List[List[Any]]
    footnote: Optional[str] = None


class ChartSpec(BaseModel):
    id: str
    chart_type: Literal["bar", "funnel", "waterfall", "donut", "line", "heatmap"]
    title: str
    option: Dict[str, Any]                                  # Valid ECharts option JSON


class DQEntry(BaseModel):
    code: str
    rule_name: str
    severity: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    affected_count: int
    description: str
    resolution: str
    sample_identifiers: List[str] = Field(default_factory=list)


class ChipCandidate(BaseModel):
    id: str
    label: str
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: str


class ToolResult(BaseModel):
    tool: str
    facts: List[Fact] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    charts: List[ChartSpec] = Field(default_factory=list)
    dq: List[DQEntry] = Field(default_factory=list)
    followups: List[ChipCandidate] = Field(default_factory=list)
    template: str = ""                                      # Deterministic narrative for degraded mode
    audit: Dict[str, Any] = Field(default_factory=dict)


class SnapshotInfo(BaseModel):
    id: str
    fetched_at: str
    age_s: float
    boards: List[str]
    source: str = "monday"
    checksum: str = ""


class CallInfo(BaseModel):
    tool: str
    args: Dict[str, Any]
    fact_ids: List[str]
    ms: float
    cache: bool = False


class RowAccounting(BaseModel):
    considered: int
    used: int
    excluded: List[Dict[str, Any]] = Field(default_factory=list)


class Receipt(BaseModel):
    confidence: Literal["high", "medium", "low"]
    as_of: str
    period: Optional[str] = None
    snapshot: Optional[SnapshotInfo] = None
    calls: List[CallInfo] = Field(default_factory=list)
    rows: RowAccounting = Field(default_factory=lambda: RowAccounting(considered=0, used=0))
    normalizations: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    definitions: List[Dict[str, Any]] = Field(default_factory=list)
    llm: List[Dict[str, Any]] = Field(default_factory=list)
    verifier: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# Formatting Utilities
# -------------------------------------------------------------------------

def format_inr(val: Optional[Union[float, int]]) -> str:
    """
    Standard Indian Rupee currency display formatting.
    1 Crore = 10,000,000 (1e7)
    1 Lakh = 100,000 (1e5)
    """
    if val is None:
        return "₹0.00"
    v = float(val)
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    if abs_v >= 1e7:
        return f"{sign}₹{abs_v / 1e7:.2f} Cr"
    elif abs_v >= 1e5:
        return f"{sign}₹{abs_v / 1e5:.2f} L"
    else:
        return f"{sign}₹{abs_v:,.2f}"


def format_pct(val: Optional[Union[float, int]]) -> str:
    if val is None:
        return "0.0%"
    return f"{float(val):.1f}%"


def format_count(val: Optional[Union[float, int]], noun: str = "") -> str:
    if val is None:
        return f"0 {noun}".strip()
    c = int(round(float(val)))
    return f"{c:,} {noun}".strip()


# -------------------------------------------------------------------------
# Contract Loader
# -------------------------------------------------------------------------

class ContractManager:
    """
    Thread-safe contract loader that reads YAML files from contracts/ directory.
    """
    def __init__(self, contracts_dir: Optional[Path] = None):
        if contracts_dir is None:
            # Look relative to project root or contracts directory
            curr = Path(__file__).resolve().parent
            candidates = [
                curr.parent.parent / "contracts",
                curr.parent / "contracts",
                Path("contracts").resolve(),
            ]
            contracts_dir = next((c for c in candidates if c.exists()), candidates[0])

        self.contracts_dir = contracts_dir
        self._cache: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        files = ["metrics", "sectors", "stages", "periods", "ambiguity", "schema_map"]
        for f in files:
            p = self.contracts_dir / f"{f}.yaml"
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    self._cache[f] = yaml.safe_load(fh)
            else:
                self._cache[f] = {}

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._cache.get("metrics", {}).get("metrics", {})

    @property
    def sectors(self) -> Dict[str, Any]:
        return self._cache.get("sectors", {})

    @property
    def stages(self) -> Dict[str, Any]:
        return self._cache.get("stages", {})

    @property
    def periods(self) -> Dict[str, Any]:
        return self._cache.get("periods", {})

    @property
    def ambiguity(self) -> Dict[str, Any]:
        return self._cache.get("ambiguity", {})

    @property
    def schema_map(self) -> Dict[str, Any]:
        return self._cache.get("schema_map", {})

    def get_contract(self, name: str) -> Dict[str, Any]:
        return self._cache.get(name, {})

    def get_metric_def(self, key: str) -> Optional[Dict[str, Any]]:
        return self.metrics.get(key)

    def is_canonical_sector(self, sector_name: str) -> bool:
        canonical_items = self.sectors.get("canonical_sectors", [])
        canonical_list = [
            s.get("name") if isinstance(s, dict) else s for s in canonical_items
        ]
        return sector_name in canonical_list

    def resolve_sector_alias(self, alias: str) -> str:
        clean = alias.strip().lower()
        for item in self.sectors.get("canonical_sectors", []):
            if isinstance(item, dict):
                c_name = item.get("name", "")
                if c_name.lower() == clean:
                    return c_name
                for a in item.get("aliases", []):
                    if a.lower() == clean:
                        return c_name
        return alias


contract_manager = ContractManager()
