"""Suite 2 — Classifier endpoint (POST /classify)."""
import time
import pytest
from conftest import HIRING_DESCRIPTION


def test_classify_hiring_description(client):
    r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
    assert r.status_code == 200, r.text
    body = r.json()
    # Required fields
    assert "domain" in body
    assert body["complexity"] in ("low", "medium", "high")
    assert isinstance(body["risk_profile"], str) and len(body["risk_profile"]) > 0
    assert isinstance(body["agent_count_estimate"], int) and body["agent_count_estimate"] > 0
    assert isinstance(body["tool_count_estimate"], int) and body["tool_count_estimate"] > 0
    assert isinstance(body["has_external_api"], bool)


def test_classify_domain_is_hr_related(client):
    r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
    domain = r.json()["domain"].lower()
    assert any(kw in domain for kw in ("hr", "recruit", "hiring", "human")), (
        f"Expected HR-related domain, got: {domain}"
    )


def test_classify_hiring_is_high_risk(client):
    r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
    body = r.json()
    risk = body["risk_profile"].lower()
    # Should mention bias or email as risk factors
    assert any(kw in risk for kw in ("bias", "email", "outbound", "scoring", "risk")), (
        f"Expected risk mention, got: {risk}"
    )


def test_classify_low_risk_use_case(client):
    r = client.post(
        "/classify",
        json={"description": "Summarize a news article and return bullet points."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["complexity"] in ("low", "medium")


def test_classify_rejects_empty_description(client):
    r = client.post("/classify", json={"description": ""})
    # Should return 422 (validation error) or 400
    assert r.status_code in (400, 422)


def test_classify_latency(client):
    t0 = time.perf_counter()
    client.post("/classify", json={"description": HIRING_DESCRIPTION})
    elapsed = (time.perf_counter() - t0) * 1000
    assert elapsed < 5000, f"Classify too slow: {elapsed:.0f}ms (Haiku should be <5s)"
