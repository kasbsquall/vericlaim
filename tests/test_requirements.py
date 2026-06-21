"""Unit tests for the CAP requirements parser.

The buyer's claim can arrive as a dict, a JSON string, or wrapped in a {"text": "<json>"}
envelope — which is exactly what the CROO store's "Hire" box produces and what made real
buyer orders return DENIED $0 until the parser learned to unwrap it.
"""
import pytest

from cap_handler import _parse_requirements


def test_plain_claim_dict_passthrough():
    claim = {"claim_number": "CLM-1", "policy": {"deductible": 0}, "amount_requested": 12000}
    assert _parse_requirements(claim) == claim


def test_json_string_is_parsed():
    out = _parse_requirements('{"claim_number": "CLM-1", "amount_requested": 12000}')
    assert out["claim_number"] == "CLM-1"
    assert out["amount_requested"] == 12000


def test_text_envelope_is_unwrapped():
    # The real CROO store shape that caused the DENIED $0 bug.
    inner = '{"claim_number": "CLM-2024-04471", "policy": {"deductible": 0}, "amount_requested": 12000}'
    out = _parse_requirements({"text": inner})
    assert out["claim_number"] == "CLM-2024-04471"
    assert out["amount_requested"] == 12000
    assert "policy" in out


def test_raw_text_envelope_is_unwrapped():
    out = _parse_requirements({"raw_text": '{"claim_number": "X", "amount_requested": 500}'})
    assert out["claim_number"] == "X"


def test_invalid_requirements_raises():
    with pytest.raises(ValueError):
        _parse_requirements(12345)
