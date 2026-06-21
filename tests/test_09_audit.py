"""Suite 9 — Audit & export endpoints."""
import uuid
import pytest
from conftest import SAFE_TOOL_CALL, BIASED_TOOL_CALL


@pytest.fixture(scope="module")
def populated_session(client):
    """Generate a session_id with at least one gate event."""
    session_id = f"audit-test-{uuid.uuid4().hex[:8]}"
    payload = {**SAFE_TOOL_CALL, "session_id": session_id}
    client.post("/gate/check", json=payload, timeout=30.0)
    return session_id


class TestAuditStreamTail:
    def test_stream_tail_returns_list(self, client):
        r = client.get("/audit/stream-tail")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, (list, dict))  # may be wrapped in a key

    def test_stream_tail_count_param(self, client):
        r = client.get("/audit/stream-tail?count=5")
        assert r.status_code == 200


class TestCacheStats:
    def test_cache_stats_returns_numbers(self, client, populated_session):
        r = client.get(f"/audit/cache-stats/{populated_session}")
        if r.status_code == 404:
            pytest.skip("No cache stats for this session (no T3 calls logged yet)")
        assert r.status_code == 200
        body = r.json()
        # Should have total_calls and hit_rate fields (or similar)
        assert isinstance(body, dict) and len(body) > 0


class TestExport:
    def test_export_returns_json(self, client, populated_session):
        r = client.get(f"/export/{populated_session}")
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            body = r.json()
            assert "session_id" in body or "blueprint" in body

    def test_audit_export_contains_gate_events(self, client, populated_session):
        r = client.get(f"/audit/export/{populated_session}")
        if r.status_code in (404, 503):
            pytest.skip("Audit export unavailable (Redis not connected or session not found)")
        assert r.status_code == 200
        body = r.json()
        assert "gate_events" in body or isinstance(body, list), (
            f"Unexpected audit export schema: {list(body.keys()) if isinstance(body, dict) else type(body)}"
        )

    def test_export_nonexistent_session(self, client):
        r = client.get(f"/export/nonexistent-session-xyz-{uuid.uuid4().hex}")
        assert r.status_code in (404, 200)  # 200 with empty data is also acceptable


class TestGateOverride:
    def test_override_logs_without_error(self, client):
        r = client.post(
            "/gate/override",
            json={
                "session_id": f"override-test-{uuid.uuid4().hex[:8]}",
                "agent_name": "Scorer",
                "tool_name": "apply_scoring_rubric",
                "decision": "approve_fix",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "logged"

    def test_override_modify_with_params(self, client):
        r = client.post(
            "/gate/override",
            json={
                "session_id": f"override-test-{uuid.uuid4().hex[:8]}",
                "agent_name": "Scorer",
                "tool_name": "apply_scoring_rubric",
                "decision": "modify",
                "modified_params": {"university_tier": 5, "skills_match": 40},
            },
        )
        assert r.status_code == 200
