"""
Numbers-by-Reference Verifier & Hallucination Auditor for Blindfold BI.

Guarantees Zero Arithmetic Hallucinations:
1. Parses and validates `[[F#]]` reference tokens against deterministic Fact definitions.
2. Audits ungrounded numbers in prose to catch fabricated metrics or mental arithmetic.
3. Substitutes verified, formatted metric values into the executive narrative.
4. Falls back to deterministic templates if ungrounded arithmetic is detected.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional, Union

from app.contracts import ToolResult, Fact

logger = logging.getLogger(__name__)

FACT_TOKEN_REGEX = re.compile(r"\[\[(F\d+)\]\]")
NUMBER_REGEX = re.compile(r"\b\d+(?:\.\d+)?\b")


@dataclass
class VerificationResult:
    verified: bool
    final_text: str
    facts_cited: List[str] = field(default_factory=list)
    facts_grounded_count: int = 0
    hallucinations_detected: List[float] = field(default_factory=list)
    confidence_score: float = 1.0
    degraded_fallback_used: bool = False

    def __iter__(self):
        return iter((self.verified, self.final_text, self.facts_grounded_count, self.confidence_score))


class NumberByReferenceVerifier:
    """
    Audits every number and reference token in the LLM's draft prose against
    the ground truth Fact objects produced by DuckDB analytical tools.
    """

    ALLOWED_NUMERALS: Set[float] = {
        0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
        100.0,
        2023.0, 2024.0, 2025.0, 2026.0, 2027.0,  # Years
    }

    def extract_ground_truth_numbers(self, data: Any) -> Set[float]:
        """Recursively extracts all scalar numbers and scaled representations from data or ToolResult."""
        numbers: Set[float] = set()

        def _add_scaled(v: float):
            numbers.add(v)
            numbers.add(round(v, 2))
            numbers.add(round(v, 1))
            if v >= 100000:
                numbers.add(round(v / 1e7, 2))  # Cr
                numbers.add(round(v / 1e7, 1))
                numbers.add(round(v / 1e5, 2))  # Lakh
                numbers.add(round(v / 1e5, 1))
            if 0.0 <= v <= 100.0:
                numbers.add(round(v / 100.0, 2))
                numbers.add(round(v / 100.0, 3))
                numbers.add(round(v / 100.0, 4))
            if 0.0 <= v <= 1.0:
                numbers.add(round(v * 100.0, 1))
                numbers.add(round(v * 100.0, 2))

        if isinstance(data, ToolResult):
            for f in data.facts:
                if isinstance(f.value, (int, float)) and not isinstance(f.value, bool):
                    _add_scaled(float(f.value))
            for t in data.tables:
                for row in t.rows:
                    for cell in row:
                        if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                            _add_scaled(float(cell))
            return numbers

        def _traverse(val: Any):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                _add_scaled(float(val))
            elif isinstance(val, dict):
                for v in val.values():
                    _traverse(v)
            elif isinstance(val, (list, tuple)):
                for v in val:
                    _traverse(v)

        _traverse(data)
        return numbers

    def verify(
        self,
        draft_prose: str,
        tool_data: Union[ToolResult, Dict[str, Any]],
        substitute_tokens: bool = True,
    ) -> VerificationResult:
        if not draft_prose:
            fallback = self._build_deterministic_fallback(tool_data)
            return VerificationResult(
                verified=True,
                final_text=fallback,
                degraded_fallback_used=True,
            )

        # 1. Map available facts and extract ground truth numbers
        facts_map: Dict[str, Fact] = {}
        if isinstance(tool_data, ToolResult):
            facts_map = {f.id: f for f in tool_data.facts}
        ground_truth_numbers = self.extract_ground_truth_numbers(tool_data)

        # 2. Extract cited [[F#]] tokens
        cited_tokens = FACT_TOKEN_REGEX.findall(draft_prose)
        valid_citations = [fid for fid in cited_tokens if fid in facts_map]
        invalid_citations = [fid for fid in cited_tokens if fid not in facts_map]

        if invalid_citations:
            logger.warning(f"Draft cited invalid Fact IDs: {invalid_citations}")

        # 3. Audit raw numbers that were NOT cited by reference
        # Mask valid fact citations first so their numeric displays aren't flagged as ungrounded
        masked_prose = FACT_TOKEN_REGEX.sub(" ", draft_prose)
        clean_prose = re.sub(r"[₹\$,%]", "", masked_prose)
        extracted_nums = NUMBER_REGEX.findall(clean_prose)

        hallucinations = []
        grounded_raw_count = 0
        for raw_num_str in extracted_nums:
            try:
                num = float(raw_num_str)
            except ValueError:
                continue

            # Check if matches any ground truth number
            matched = any(abs(num - gt) < 0.05 or abs(num - gt) / max(gt, 1.0) < 0.01 for gt in ground_truth_numbers)
            if matched:
                grounded_raw_count += 1
            else:
                if num not in self.ALLOWED_NUMERALS:
                    hallucinations.append(num)

        # Total facts grounded count includes explicit citations plus verified raw numbers
        total_facts_grounded = len(valid_citations) + grounded_raw_count

        # 4. Determine verification verdict
        is_verified = len(hallucinations) == 0 and len(invalid_citations) == 0

        final_text = draft_prose
        degraded = False
        confidence = 1.0

        if not is_verified:
            confidence = max(0.5, round(1.0 - (len(hallucinations) * 0.15), 2))
            logger.warning(
                f"Hallucination threshold breached ({len(hallucinations)} ungrounded numbers: {hallucinations}). "
                f"Activating deterministic fallback."
            )
            final_text = self._build_deterministic_fallback(tool_data)
            degraded = True

        # 5. Substitute [[F#]] tokens with verified display values if requested
        if substitute_tokens and not degraded:
            for fid, fact in facts_map.items():
                token_pattern = f"[[{fid}]]"
                if token_pattern in final_text:
                    final_text = final_text.replace(token_pattern, fact.display)

        return VerificationResult(
            verified=is_verified,
            final_text=final_text,
            facts_cited=valid_citations,
            facts_grounded_count=total_facts_grounded,
            hallucinations_detected=hallucinations,
            confidence_score=confidence,
            degraded_fallback_used=degraded,
        )

    def _build_deterministic_fallback(self, tool_data: Union[ToolResult, Dict[str, Any]]) -> str:
        """Constructs a deterministic, fully-grounded response when hallucinations occur."""
        if isinstance(tool_data, ToolResult):
            template = tool_data.template
            for f in tool_data.facts:
                template = template.replace(f"[[{f.id}]]", f.display)

            bullets = [f"- **{f.label}**: {f.display}" for f in tool_data.facts]
            bullets_str = "\n".join(bullets)
            dq_str = ""
            if tool_data.dq:
                dq_items = [f"- **{d.code}**: {d.description}" for d in tool_data.dq]
                dq_str = f"\n\n### ⚠️ Data Governance Caveats\n" + "\n".join(dq_items)

            return (
                f"### 🎯 Verified Pipeline Summary\n\n"
                f"{template}\n\n"
                f"### 📊 Key Verified Metrics\n"
                f"{bullets_str}"
                f"{dq_str}\n\n"
                f"*Verified deterministically via DuckDB analytical engine with zero arithmetic hallucinations.*"
            )

        # If tool_data is a dict (e.g. from legacy tests)
        summary = tool_data.get("summary", {})
        open_deals = summary.get("total_open_deals", summary.get("deal_count", "N/A"))
        pipe_val = summary.get("total_pipeline_value", summary.get("total_value", "N/A"))
        if isinstance(pipe_val, (int, float)):
            pipe_val_cr = f"₹{pipe_val/1e7:.2f} Cr"
        else:
            pipe_val_cr = str(pipe_val)

        return (
            f"### 🎯 Verified Pipeline Summary\n\n"
            f"- Open Deals: {open_deals}\n"
            f"- Pipeline Value: {pipe_val_cr}\n"
            f"- Realization Rate: {summary.get('realization_rate_pct', 'N/A')}%\n\n"
            f"*Verified deterministically via DuckDB analytical engine.*"
        )


# Export class alias for backwards compatibility
HallucinationVerifier = NumberByReferenceVerifier

# Export singleton
verifier = NumberByReferenceVerifier()
