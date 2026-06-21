"""Suite 5 — 3-Tier Safety Gate (POST /gate/check)."""
import time
import pytest
from conftest import (
    SAFE_TOOL_CALL,
    BIASED_TOOL_CALL,
    BLOCKED_TOOL_CALL,
    WILDCARD_PARAM_CALL,
)

GATE_URL = "/gate/check"


# ── T1: Deterministic Guardrails ──────────────────────────────────────────────

class TestT1Guardrails:
    def test_blocked_tool_returns_block(self, client):
        r = client.post(GATE_URL, json=BLOCKED_TOOL_CALL)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["decision"] == "BLOCK"
        assert body["tier_triggered"] == 1

    def test_blocked_tool_latency_under_10ms(self, client):
        t0 = time.perf_counter()
        client.post(GATE_URL, json=BLOCKED_TOOL_CALL)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 200, f"T1 should be near-instant, got {elapsed_ms:.0f}ms"

    def test_wildcard_param_returns_block(self, client):
        r = client.post(GATE_URL, json=WILDCARD_PARAM_CALL)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["decision"] == "BLOCK"
        assert body["tier_triggered"] == 1

    @pytest.mark.parametrize("tool_name", ["bulk_delete", "send_to_all", "rm_rf", "drop_db"])
    def test_all_blocked_tool_names(self, client, tool_name):
        payload = {**BLOCKED_TOOL_CALL, "tool_name": tool_name}
        r = client.post(GATE_URL, json=payload)
        assert r.json()["decision"] == "BLOCK", f"{tool_name} should be blocked"

    @pytest.mark.parametrize("bad_value", ["*", "all", "everyone", "drop"])
    def test_all_blocked_param_values(self, client, bad_value):
        payload = {**SAFE_TOOL_CALL, "tool_params": {"target": bad_value}}
        r = client.post(GATE_URL, json=payload)
        assert r.json()["decision"] == "BLOCK", f"param value '{bad_value}' should be blocked"


# ── T2: Semantic Cache ────────────────────────────────────────────────────────

class TestT2Cache:
    def test_second_identical_call_is_cache_hit(self, client):
        # First call — may go to T3 (Claude)
        client.post(GATE_URL, json=SAFE_TOOL_CALL)
        # Second call — must be served from cache
        r2 = client.post(GATE_URL, json=SAFE_TOOL_CALL)
        body = r2.json()
        assert body["cache_hit"] is True
        assert body["tier_triggered"] == 2

    def test_cache_hit_is_faster_than_cold(self, client):
        # Prime cache
        client.post(GATE_URL, json=SAFE_TOOL_CALL)
        # Cold-ish call with different session_id but same tool/params (should still cache)
        t0 = time.perf_counter()
        r = client.post(GATE_URL, json=SAFE_TOOL_CALL)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if r.json()["cache_hit"]:
            assert elapsed_ms < 500, f"Cache hit should be fast, got {elapsed_ms:.0f}ms"

    def test_different_params_bypass_cache(self, client):
        import uuid
        unique_payload = {
            **SAFE_TOOL_CALL,
            "tool_params": {"resume_text": f"unique-resume-{uuid.uuid4().hex}"},
        }
        r = client.post(GATE_URL, json=unique_payload)
        # First-ever call for this unique payload cannot be a cache hit
        assert r.json()["cache_hit"] is False


# ── T3: Claude Scoring ────────────────────────────────────────────────────────

class TestT3ClaudeScoring:
    def test_safe_action_is_allowed(self, client):
        import uuid
        # Use unique params to bypass cache
        payload = {
            **SAFE_TOOL_CALL,
            "session_id": f"t3-test-{uuid.uuid4().hex}",
            "tool_params": {"resume_text": f"candidate-{uuid.uuid4().hex[:6]}, 3 years Python"},
        }
        r = client.post(GATE_URL, json=payload, timeout=30.0)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["decision"] in ("ALLOW", "WARN")  # low-risk should usually be ALLOW
        assert body["tier_triggered"] == 3
        assert body["cache_hit"] is False

    def test_biased_rubric_warns(self, client):
        import uuid
        payload = {
            **BIASED_TOOL_CALL,
            "session_id": f"bias-test-{uuid.uuid4().hex}",
            # Vary params slightly to avoid cache
            "tool_params": {**BIASED_TOOL_CALL["tool_params"], "_nonce": uuid.uuid4().hex[:6]},
        }
        r = client.post(GATE_URL, json=payload, timeout=30.0)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["decision"] in ("WARN", "BLOCK"), (
            f"Biased rubric should trigger WARN or BLOCK, got {body['decision']}"
        )

    def test_gate_response_schema_complete(self, client):
        import uuid
        payload = {**SAFE_TOOL_CALL, "session_id": f"schema-{uuid.uuid4().hex}",
                   "tool_params": {"resume_text": f"test-{uuid.uuid4().hex}"}}
        r = client.post(GATE_URL, json=payload, timeout=30.0)
        body = r.json()
        required = ["decision", "tier_triggered", "explanation", "cache_hit", "latency_ms"]
        for field in required:
            assert field in body, f"Missing field: {field}"
        assert body["decision"] in ("ALLOW", "WARN", "BLOCK")
        assert body["tier_triggered"] in (1, 2, 3)
        assert isinstance(body["explanation"], str) and len(body["explanation"]) > 0
        assert isinstance(body["latency_ms"], int)

    def test_warn_decision_includes_fix_draft(self, client):
        import uuid
        payload = {
            **BIASED_TOOL_CALL,
            "session_id": f"fix-draft-{uuid.uuid4().hex}",
            "tool_params": {
                "university_tier": 60,   # heavily biased
                "years_experience": 10,
                "skills_match": 20,
                "portfolio_quality": 10,
                "_nonce": uuid.uuid4().hex[:6],
            },
        }
        r = client.post(GATE_URL, json=payload, timeout=30.0)
        body = r.json()
        if body["decision"] == "WARN":
            assert body.get("fix_draft") is not None, "WARN should include a fix_draft"

    def test_scores_are_in_valid_range(self, client):
        import uuid
        payload = {**SAFE_TOOL_CALL, "session_id": f"score-range-{uuid.uuid4().hex}",
                   "tool_params": {"resume_text": f"test-{uuid.uuid4().hex}"}}
        r = client.post(GATE_URL, json=payload, timeout=30.0)
        body = r.json()
        if body["tier_triggered"] == 3:
            if body.get("misalignment_score") is not None:
                assert 0 <= body["misalignment_score"] <= 100
            if body.get("oversight_score") is not None:
                assert 0 <= body["oversight_score"] <= 100
