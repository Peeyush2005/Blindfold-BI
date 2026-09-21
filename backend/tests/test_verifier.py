import pytest
from app.core.verifier import HallucinationVerifier

def test_extract_ground_truth_numbers():
    verifier = HallucinationVerifier()
    data = {
        "summary": {
            "total_value": 10000000.0, # 1 Cr
            "deal_count": 42,
            "rate_pct": 50.99
        },
        "nested": [
            {"val": 500000.0} # 5 Lakh
        ]
    }
    nums = verifier.extract_ground_truth_numbers(data)
    assert 10000000.0 in nums
    assert 1.0 in nums # 1 Cr
    assert 42.0 in nums
    assert 50.99 in nums
    assert 5.0 in nums # 5 Lakh

def test_verifier_accepts_grounded_text():
    verifier = HallucinationVerifier()
    tool_data = {
        "summary": {
            "total_pipeline_value": 688152293.17,
            "total_open_deals": 49,
            "realization_rate_pct": 50.99
        }
    }

    draft = "We have 49 open deals totaling ₹68.82 Cr with a 50.99% realization rate."
    is_verified, text, facts_grounded, score = verifier.verify(draft, tool_data)

    assert is_verified is True
    assert facts_grounded >= 2
    assert score == 1.0

def test_verifier_rejects_hallucinated_numbers():
    verifier = HallucinationVerifier()
    tool_data = {
        "summary": {
            "total_open_deals": 49,
            "total_pipeline_value": 688152293.17
        }
    }

    # Draft with hallucinated arithmetic: claims 999 deals and 88.45%
    draft = "There are 999 open deals with a 88.45% success rate."
    is_verified, fallback_text, facts_grounded, score = verifier.verify(draft, tool_data)

    assert is_verified is False
    assert score < 1.0
    # Fallback templated text should be returned
    assert "Verified Pipeline Summary" in fallback_text
    assert "49" in fallback_text


def test_verifier_substitutes_fact_tokens():
    from app.contracts import ToolResult, Fact

    verifier = HallucinationVerifier()
    tool_result = ToolResult(
        tool="get_pipeline_summary",
        facts=[
            Fact(id="F1", metric="open_deals", label="Open Deals", value=49, unit="count", display="49 deals", role="primary"),
            Fact(id="F2", metric="pipeline_value", label="Pipeline Value", value=688152293.17, unit="INR", display="₹68.82 Cr", role="primary"),
        ],
    )

    draft = "Current pipeline shows [[F1]] valued at [[F2]] across sectors."
    res = verifier.verify(draft, tool_result, substitute_tokens=True)

    assert res.verified is True
    assert "49 deals" in res.final_text
    assert "₹68.82 Cr" in res.final_text
    assert "[[F1]]" not in res.final_text
    assert "[[F2]]" not in res.final_text


def test_verifier_allows_structural_labels():
    from app.contracts import ToolResult, Fact

    verifier = HallucinationVerifier()
    tool_result = ToolResult(
        tool="get_aging_summary",
        facts=[
            Fact(id="F1", metric="receivable_amount", label="Overdue Receivables", value=36291748.87, unit="INR", display="₹3.63 Cr", role="primary"),
        ],
    )

    draft = (
        "As of 15 Jan 2026 for Q4 FY25-26, under rule DQ009 and 90-day aging thresholds, "
        "the 1st priority outstanding receivables stand at [[F1]]."
    )
    res = verifier.verify(draft, tool_result, substitute_tokens=True)

    assert res.verified is True
    assert len(res.hallucinations_detected) == 0
    assert "₹3.63 Cr" in res.final_text


def test_verifier_audit_emits_offending_spans():
    from app.contracts import ToolResult, Fact

    verifier = HallucinationVerifier()
    tool_result = ToolResult(
        tool="get_pipeline_summary",
        facts=[
            Fact(id="F1", metric="open_deals", label="Open Deals", value=49, unit="count", display="49 deals", role="primary"),
        ],
    )

    draft = "There are [[F1]] totaling ₹999.50 Cr with 88.5% conversion rate."
    audit_res = verifier.audit_claims(draft, tool_result)

    assert audit_res.verified is False
    assert len(audit_res.offending_spans) > 0
    # Confirms ungrounded claims are captured in offending_spans for repair
    spans_str = " ".join(audit_res.offending_spans)
    assert "999" in spans_str or "88.5" in spans_str


def test_question_aware_fallback_generation():
    from app.contracts import ToolResult, Fact, StructuredIntent

    verifier = HallucinationVerifier()
    tool_result = ToolResult(
        tool="get_pipeline_summary",
        facts=[
            Fact(id="F1", metric="pipeline_value", label="Mining Open Pipeline", value=15200000.0, unit="INR", display="₹1.52 Cr", role="primary"),
            Fact(id="F2", metric="open_deals", label="Open Deals Count", value=8, unit="count", display="8 deals", role="support"),
        ],
    )
    intent = StructuredIntent(
        raw_query="What is the open pipeline for Mining sector?",
        tool_name="get_pipeline_summary",
        filters={"sector": "Mining"},
    )

    fallback = verifier.build_question_aware_fallback(
        tool_result, intent=intent, question="What is the open pipeline for Mining sector?"
    )

    assert "Mining" in fallback
    assert "₹1.52 Cr" in fallback
    assert "8 deals" in fallback

