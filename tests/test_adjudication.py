"""Unit tests for VeriClaim's pure adjudication logic.

Covers the three deterministic, security-relevant pieces with no DB/LLM dependency:
  - Sam's resolution parser (_strip_fences, _parse_resolution)
  - the dynamic-fraud gate that recruits Quinn (_alleges_fraud)
  - the tamper-evident SHA-256 audit (hash_resolution)
"""
from decimal import Decimal

from debate_engine import (
    _alleges_fraud,
    _parse_resolution,
    _retrieval_query,
    _strip_fences,
)
from utils.audit import hash_resolution


# ---------------- _strip_fences ----------------
def test_strip_fences_removes_json_fence():
    assert _strip_fences("```json\nDECISION: APPROVED\n```") == "DECISION: APPROVED"


def test_strip_fences_removes_bare_fence():
    assert _strip_fences("```\nhello world\n```") == "hello world"


def test_strip_fences_leaves_plain_text_untouched():
    assert _strip_fences("DECISION: DENIED") == "DECISION: DENIED"


# ---------------- _parse_resolution ----------------
def test_parse_approved_with_amount_and_clause():
    r = _parse_resolution("DECISION: APPROVED\nAPPROVED AMOUNT: $12,000.00\nReasoning: under §12.1")
    assert r["decision"] == "APPROVED"
    assert r["approved_amount"] == Decimal("12000.00")
    assert r["cited_clauses"] == ["§12.1"]


def test_parse_denied_has_no_amount():
    r = _parse_resolution("DECISION: DENIED")
    assert r["decision"] == "DENIED"
    assert r["approved_amount"] is None


def test_parse_partial():
    assert _parse_resolution("DECISION: PARTIAL")["decision"] == "PARTIAL"


def test_parse_unclear_when_no_verdict():
    assert _parse_resolution("the panel could not agree")["decision"] == "UNCLEAR"


def test_parse_tolerates_bold_markdown():
    assert _parse_resolution("DECISION: **APPROVED**")["decision"] == "APPROVED"


def test_parse_amount_without_dollar_sign():
    assert _parse_resolution("DECISION: APPROVED\nAPPROVED AMOUNT: 3700")["approved_amount"] == Decimal("3700")


def test_parse_clauses_are_deduped_and_sorted():
    r = _parse_resolution("cites §7.3, then §12.1, then §7.3 again")
    assert r["cited_clauses"] == ["§12.1", "§7.3"]


# ---------------- _alleges_fraud (Quinn recruitment gate) ----------------
def test_fraud_gate_trips_on_rideshare_denial():
    assert _alleges_fraud({"original_denial_reason": "undisclosed commercial rideshare use"}) is True


def test_fraud_gate_trips_on_misrepresentation():
    assert _alleges_fraud({"incident_description": "material misrepresentation on the application"}) is True


def test_fraud_gate_is_case_insensitive():
    assert _alleges_fraud({"original_denial_reason": "FRAUD suspected"}) is True


def test_fraud_gate_checks_incident_description_too():
    assert _alleges_fraud({"incident_description": "the claim appears staged"}) is True


def test_fraud_gate_quiet_on_ordinary_collision():
    payload = {
        "original_denial_reason": "mechanical failure exclusion under §7.3",
        "incident_description": "vehicle struck a guardrail at 35 mph",
    }
    assert _alleges_fraud(payload) is False


# ---------------- _retrieval_query ----------------
def test_retrieval_query_joins_denial_and_incident_fields():
    q = _retrieval_query(
        {"original_denial_reason": "DENIAL", "incident_type": "collision", "incident_description": "GUARDRAIL"}
    )
    assert "DENIAL" in q and "collision" in q and "GUARDRAIL" in q


# ---------------- hash_resolution (tamper-evident audit) ----------------
CLAIM = {"claim_number": "CLM-2024-04471", "amount_requested": 12000}
TURNS = [("blake", "leans denied"), ("sam", "rules approved")]


def test_hash_is_64_char_hex():
    h = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)
    assert len(h["sha256"]) == 64
    int(h["sha256"], 16)  # raises if not valid hex


def test_hash_is_deterministic():
    a = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)["sha256"]
    b = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)["sha256"]
    assert a == b


def test_hash_changes_when_decision_changes():
    a = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)["sha256"]
    b = hash_resolution(CLAIM, TURNS, "DENIED", 12000.0)["sha256"]
    assert a != b


def test_hash_changes_when_amount_changes():
    a = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)["sha256"]
    b = hash_resolution(CLAIM, TURNS, "APPROVED", 3700.0)["sha256"]
    assert a != b


def test_hash_changes_when_transcript_is_tampered():
    a = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)["sha256"]
    tampered = [("blake", "leans denied"), ("sam", "rules approved — edited")]
    b = hash_resolution(CLAIM, tampered, "APPROVED", 12000.0)["sha256"]
    assert a != b


def test_hash_metadata_reports_turn_count_and_coverage():
    h = hash_resolution(CLAIM, TURNS, "APPROVED", 12000.0)
    assert h["message_count"] == 2
    assert h["hash_algorithm"] == "sha256"
    assert set(h["covers"]) == {"claim_input", "transcript", "decision", "approved_amount"}
