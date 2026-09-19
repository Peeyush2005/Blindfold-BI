"""
Data Quality (DQ) Ledger for Blindfold BI.
Tracks and audits all data hygiene anomalies, quirks, and transformations (DQ001 - DQ016)
across Deals and Work Orders boards.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class DQAnomaly:
    code: str
    rule_name: str
    severity: str  # "HIGH", "MEDIUM", "LOW", "INFO"
    description: str
    affected_count: int
    resolution: str
    sample_identifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "description": self.description,
            "affected_count": self.affected_count,
            "resolution": self.resolution,
            "sample_identifiers": self.sample_identifiers,
        }


class DQLedger:
    def __init__(self):
        self.anomalies: Dict[str, DQAnomaly] = {}

    def record(
        self,
        code: str,
        rule_name: str,
        severity: str,
        description: str,
        affected_count: int,
        resolution: str,
        sample_identifiers: Optional[List[str]] = None,
    ) -> None:
        self.anomalies[code] = DQAnomaly(
            code=code,
            rule_name=rule_name,
            severity=severity.upper(),
            description=description,
            affected_count=affected_count,
            resolution=resolution,
            sample_identifiers=sample_identifiers or [],
        )

    def get_all(self) -> List[DQAnomaly]:
        return sorted(self.anomalies.values(), key=lambda a: a.code)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.get_all()]

    def to_dataframe(self) -> pd.DataFrame:
        records = [
            {
                "DQ Code": a.code,
                "Rule Name": a.rule_name,
                "Severity": a.severity,
                "Affected Rows": a.affected_count,
                "Description": a.description,
                "Resolution Strategy": a.resolution,
                "Sample Identifiers": ", ".join(a.sample_identifiers[:5]),
            }
            for a in self.get_all()
        ]
        return pd.DataFrame(records)

    def export_csv(self, file_path: str) -> str:
        df = self.to_dataframe()
        df.to_csv(file_path, index=False)
        return file_path

    def clear(self) -> None:
        self.anomalies.clear()


dq_ledger = DQLedger()
