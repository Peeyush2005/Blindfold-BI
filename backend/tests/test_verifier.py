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
