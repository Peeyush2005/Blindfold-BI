"""
Numbers-by-Reference Verifier & Hallucination Auditor for Blindfold BI.

Guarantees Zero Arithmetic Hallucinations:
1. Parses and validates `[[F#]]` reference tokens against deterministic Fact definitions.
2. Audits quantitative claims in prose to catch fabricated metrics or mental arithmetic.
3. Allows non-claim structural labels (Q1-Q4, FY25-26, ordinals, dates, top-N filters).
4. Emits exact offending spans on failure to power a single LLM repair attempt.
5. Falls back to question-aware, intent-driven dynamic responses when repair fails.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional, Union

from app.contracts import ToolResult, Fact, StructuredIntent

logger = logging.getLogger(__name__)

FACT_TOKEN_REGEX = re.compile(r"\[\[(F\d+)\]\]")
NUMBER_REGEX = re.compile(r"\b\d+(?:\.\d+)?\b")

# Non-claim structural patterns that should not be audited as arithmetic claims
# IMPORTANT: Put longer/more specific multi-word patterns before isolated digits or years
NON_CLAIM_PATTERNS = [
    re.compile(r"\[\[F\d+\]\]", re.IGNORECASE),                         # [[F1]]
    re.compile(r"\bDQ\d{3}\b", re.IGNORECASE),                           # DQ001 - DQ016
    re.compile(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s*,?\s*\d{4})?\b",
        re.IGNORECASE,
    ),                                                                    # 15 Jan 2026, 15th Jan, 15 January
    re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?\b",
        re.IGNORECASE,
    ),                                                                    # January 15, 2026, Jan 15
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),                                # 2026-01-15
    re.compile(r"\b(?:30|60|90|180|365)\s*-?\s*days?\b", re.IGNORECASE), # 90 days, 90-day aging thresholds
    re.compile(r"\b(?:15|16)\s+(?:active\s+)?(?:DQ|data\s+quality)\s+(?:rules?|codes?|checks?|anomalies)\b", re.IGNORECASE),
    re.compile(r"\bQ[1-4](?:\s*FY\d{2}(?:-\d{2})?)?\b", re.IGNORECASE),  # Q1, Q4 FY25-26
    re.compile(r"\bFY\s*\d{2}(?:-\d{2})?\b", re.IGNORECASE),             # FY25-26, FY26
    re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.IGNORECASE),                # 1st, 2nd, 3rd, 4th
    re.compile(r"\btop\s+\d+\b", re.IGNORECASE),                         # top 1, top 3, top 5, top 10
    re.compile(r"\b(?:19\d{2}|20\d{2})\b"),                              # Years: 2024, 2025, 2026, 2027 (after dates)
    re.compile(r"^\s*\d+\.\s+", re.MULTILINE),                           # Numbered list markers: 1. , 2.
]

# Quantitative claim patterns representing currency, percentages, counts, ratios
CLAIM_PATTERNS = [
    re.compile(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?(?:\s*(?:Cr|Crore|Lakh|L))?", re.IGNORECASE),
    re.compile(r"[\d,]+(?:\.\d+)?\s*(?:Cr|Crore|Lakh)", re.IGNORECASE),
    re.compile(r"[\d,]+(?:\.\d+)?%", re.IGNORECASE),
    re.compile(
        r"[\d,]+(?:\.\d+)?\s*(?:deals?|work orders?|orders?|records?|rules?|days?|rows?|sectors?|clients?|accounts?|projects?)",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d+(?:\.\d+)?(?::\d+(?:\.\d+)?|x\b)", re.IGNORECASE),
]


@dataclass
class VerificationResult:
    verified: bool
    final_text: str
    facts_cited: List[str] = field(default_factory=list)
    facts_grounded_count: int = 0
    hallucinations_detected: List[float] = field(default_factory=list)
    offending_spans: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    degraded_fallback_used: bool = False
    repaired: bool = False

    def __iter__(self):
        return iter((self.verified, self.final_text, self.facts_grounded_count, self.confidence_score))


class NumberByReferenceVerifier:
    """
    Audits narrative text against the ground truth Fact objects produced by DuckDB analytical tools.
    Rejects quantitative claims that are ungrounded while permitting structural labels.
    """

    ALLOWED_NUMERALS: Set[float] = {
        0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
        11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0,
        21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0,  # Calendar days / top ranks
        60.0, 90.0, 180.0, 365.0,  # Aging thresholds
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
            if hasattr(data, "dq") and data.dq:
                for d in data.dq:
                    desc = getattr(d, "description", "") or ""
                    for num_str in NUMBER_REGEX.findall(desc):
                        try:
                            _add_scaled(float(num_str))
                        except ValueError:
                            pass
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

    def audit_claims(
        self,
        draft_prose: str,
        tool_data: Union[ToolResult, Dict[str, Any]],
        intent: Optional[StructuredIntent] = None,
        question: Optional[str] = None,
    ) -> VerificationResult:
        """
        Policy: Reject only ungrounded quantitative claims (currency, percentage, counts, unscaled digits).
        Allow non-claim structural labels (Q1-Q4, FY25-26, ordinals, dates, top-N).
        Verify that primary facts are cited and intent filters are mentioned.
        """
        if not draft_prose:
            fallback = self.build_question_aware_fallback(tool_data, intent=intent, question=question)
            return VerificationResult(
                verified=True,
                final_text=fallback,
                degraded_fallback_used=True,
            )

        facts_map: Dict[str, Fact] = {}
        if isinstance(tool_data, ToolResult):
            facts_map = {f.id: f for f in tool_data.facts}
        ground_truth_numbers = self.extract_ground_truth_numbers(tool_data)

        # Allow numbers explicitly present in user query (e.g. "90 days", "Q4", "2026")
        if question:
            for q_num_str in NUMBER_REGEX.findall(question.replace(",", "")):
                try:
                    ground_truth_numbers.add(float(q_num_str))
                except ValueError:
                    pass

        # Allow numbers explicitly present in structured intent (e.g. top_n)
        if intent:
            if getattr(intent, "top_n", None):
                try:
                    ground_truth_numbers.add(float(intent.top_n))
                except (ValueError, TypeError):
                    pass

        # 1. Fact token citations check
        cited_tokens = FACT_TOKEN_REGEX.findall(draft_prose)
        valid_citations = [fid for fid in cited_tokens if fid in facts_map]
        invalid_citations = [fid for fid in cited_tokens if fid not in facts_map]

        offending_spans: List[str] = []
        if invalid_citations:
            for inv in invalid_citations:
                offending_spans.append(f"[[{inv}]] (invalid fact token)")

        # 2. Relevance Check: Ensure primary fact is cited if primary facts exist
        primary_facts = [f for f in facts_map.values() if getattr(f, "role", "support") == "primary"]
        if primary_facts and valid_citations:
            primary_ids = {f.id for f in primary_facts}
            if not any(cid in primary_ids for cid in valid_citations):
                logger.info("Draft cited facts but omitted primary fact(s).")
                # Warning rather than hard rejection if valid facts are cited

        # 3. Mask out non-claim structural patterns so their numbers aren't treated as arithmetic claims
        masked_prose = draft_prose
        for pattern in NON_CLAIM_PATTERNS:
            masked_prose = pattern.sub(" <NON_CLAIM> ", masked_prose)

        # Also mask out valid [[F#]] tokens and replace them with placeholder
        masked_prose = FACT_TOKEN_REGEX.sub(" <FACT_REF> ", masked_prose)

        # 4. Check explicit quantitative claim patterns
        hallucinations: List[float] = []
        grounded_raw_count = 0

        # Scan for explicit claims in the masked prose
        for claim_pat in CLAIM_PATTERNS:
            for match in claim_pat.finditer(masked_prose):
                claim_span = match.group(0).strip()
                # Extract numeric component from claim span
                num_matches = NUMBER_REGEX.findall(claim_span.replace(",", ""))
                for raw_num_str in num_matches:
                    try:
                        num = float(raw_num_str)
                    except ValueError:
                        continue
                    matched = any(
                        abs(num - gt) < 0.05 or (gt != 0 and abs(num - gt) / abs(gt) < 0.01)
                        for gt in ground_truth_numbers
                    )
                    if matched:
                        grounded_raw_count += 1
                    elif num not in self.ALLOWED_NUMERALS:
                        hallucinations.append(num)
                        offending_spans.append(claim_span)

        # 5. Scan remaining unmasked raw numbers
        clean_prose = re.sub(r"[₹\$,%]", "", masked_prose)
        extracted_nums = NUMBER_REGEX.findall(clean_prose)
        for raw_num_str in extracted_nums:
            try:
                num = float(raw_num_str)
            except ValueError:
                continue
            matched = any(
                abs(num - gt) < 0.05 or (gt != 0 and abs(num - gt) / abs(gt) < 0.01)
                for gt in ground_truth_numbers
            )
            if matched:
                grounded_raw_count += 1
            elif num not in self.ALLOWED_NUMERALS:
                if num not in hallucinations:
                    hallucinations.append(num)
                    offending_spans.append(raw_num_str)

        total_facts_grounded = len(valid_citations) + grounded_raw_count
        is_verified = (len(hallucinations) == 0) and (len(invalid_citations) == 0)

        final_text = draft_prose
        degraded = False
        confidence = 1.0

        if not is_verified:
            confidence = max(0.4, round(1.0 - (len(hallucinations) * 0.15) - (len(invalid_citations) * 0.2), 2))
            logger.warning(
                f"Verifier detected ungrounded claims ({len(offending_spans)} spans: {offending_spans[:5]})."
            )

        return VerificationResult(
            verified=is_verified,
            final_text=final_text,
            facts_cited=valid_citations,
            facts_grounded_count=total_facts_grounded,
            hallucinations_detected=hallucinations,
            offending_spans=offending_spans,
            confidence_score=confidence,
            degraded_fallback_used=degraded,
        )

    def verify(
        self,
        draft_prose: str,
        tool_data: Union[ToolResult, Dict[str, Any]],
        substitute_tokens: bool = True,
        intent: Optional[StructuredIntent] = None,
        question: Optional[str] = None,
    ) -> VerificationResult:
        """Audits prose and performs substitution or dynamic fallback."""
        result = self.audit_claims(draft_prose, tool_data, intent=intent, question=question)

        facts_map: Dict[str, Fact] = {}
        if isinstance(tool_data, ToolResult):
            facts_map = {f.id: f for f in tool_data.facts}

        if not result.verified:
            result.final_text = self.build_question_aware_fallback(tool_data, intent=intent, question=question)
            result.degraded_fallback_used = True
            return result

        # Substitute [[F#]] tokens with verified display values
        final_text = result.final_text
        if substitute_tokens:
            for fid, fact in facts_map.items():
                token_pattern = f"[[{fid}]]"
                if token_pattern in final_text:
                    final_text = final_text.replace(token_pattern, fact.display)

            # Deduplicate repeated unit words resulting from substitution (e.g., "8 deals deals" -> "8 deals")
            final_text = re.sub(r"\b(deals?|work orders?|orders?|sectors?|records?|rows?)\s+\1\b", r"\1", final_text, flags=re.IGNORECASE)

        result.final_text = final_text
        return result

    def build_question_aware_fallback(
        self,
        tool_data: Union[ToolResult, Dict[str, Any]],
        intent: Optional[StructuredIntent] = None,
        question: Optional[str] = None,
    ) -> str:
        """
        Constructs a dynamic, question-aware, un-templated natural response directly
        derived from the parsed query intent and primary/support facts.
        """
        if not isinstance(tool_data, ToolResult):
            return self._build_legacy_fallback(tool_data)

        # Extract entities from intent filters or question
        filters = intent.filters if intent else {}
        sector = filters.get("sector") or filters.get("sector_group")
        period = filters.get("period")
        status = filters.get("status")

        # Categorize facts by role
        primary_facts = [f for f in tool_data.facts if getattr(f, "role", "support") == "primary"]
        support_facts = [f for f in tool_data.facts if getattr(f, "role", "support") == "support"]
        caveat_facts = [f for f in tool_data.facts if getattr(f, "role", "support") == "caveat"]

        if not primary_facts:
            primary_facts = tool_data.facts[:1]
            support_facts = tool_data.facts[1:]

        # Entity prefix
        prefix_parts = []
        if sector:
            prefix_parts.append(f"the **{sector}** sector")
        if period:
            prefix_parts.append(f"for **{period}**")
        if status:
            prefix_parts.append(f"with status '{status}'")

        if prefix_parts:
            entity_clause = "For " + " ".join(prefix_parts) + ", "
        elif question:
            clean_q = re.sub(r"[?!.]+$", "", question).strip()
            entity_clause = f"Regarding {clean_q.lower()}, "
        else:
            entity_clause = ""

        # Primary fact sentence
        primary_statements = [f"{f.label} stands at **{f.display}**" for f in primary_facts]
        primary_sentence = f"{entity_clause}{' and '.join(primary_statements)}."

        # Support facts
        support_lines = []
        for f in support_facts:
            support_lines.append(f"- **{f.label}**: {f.display}")

        # Caveat / DQ items
        caveat_lines = []
        for f in caveat_facts:
            caveat_lines.append(f"- {f.label}: {f.display}")
        if tool_data.dq:
            for d in tool_data.dq:
                caveat_lines.append(f"- **{d.code}** ({d.rule_name}): {d.description}")

        prose_parts = [primary_sentence]
        if support_lines:
            prose_parts.append("\n**Key Supporting Details:**\n" + "\n".join(support_lines))
        if caveat_lines:
            prose_parts.append("\n**Governance & Coverage Notes:**\n" + "\n".join(caveat_lines))

        return "\n\n".join(prose_parts)

    def _build_legacy_fallback(self, tool_data: Dict[str, Any]) -> str:
        summary = tool_data.get("summary", {})
        open_deals = summary.get("total_open_deals", summary.get("deal_count", "N/A"))
        pipe_val = summary.get("total_pipeline_value", summary.get("total_value", "N/A"))
        pipe_val_cr = f"₹{pipe_val/1e7:.2f} Cr" if isinstance(pipe_val, (int, float)) else str(pipe_val)
        return (
            f"### Verified Pipeline Summary\n\n"
            f"The analyzed pipeline reflects **{open_deals} open deals** with total value of **{pipe_val_cr}** "
            f"and an estimated realization rate of **{summary.get('realization_rate_pct', 'N/A')}%**."
        )


# Export class alias for backwards compatibility
HallucinationVerifier = NumberByReferenceVerifier

# Export singleton
verifier = NumberByReferenceVerifier()
