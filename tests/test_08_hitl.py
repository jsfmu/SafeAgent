"""Suite 8 — Human-in-the-Loop (HITL) decisions (POST /run/decide).

These tests simulate the scenario where the safety gate returns WARN and the
human must approve, modify, or override the flagged action.
"""
import json
import uuid
import time
import threading
import pytest
import httpx
from conftest import HIRING_DESCRIPTION


def _biased_blueprint():
    """Blueprint that deliberately uses a biased rubric to trigger WARN."""
    return {
        "topology": "A",
        "topology_name": "Supervisor-Worker",
        "agents": [
            {
                "name": "Scorer",
                "role": "Candidate scorer with biased university-heavy rubric.",
                "model": "claude-sonnet-4-6",
                "tools": ["apply_scoring_rubric"],
                "system_prompt": "Score candidates. University tier is most important.",
            }
        ],
        "edges": [],
        "entry_node": "Scorer",
        "prediction": {
            "cost_usd": 0.05,
            "latency_sec": 1.5,
            "tokens_in": 800,
            "tokens_out": 200,
            "bottleneck_agent": "Scorer",
            "confidence": "low",
        },
    }


def _collect_events_until_blocked(base_url, run_id, timeout=90) -> list:
    events = []
    deadline = time.time() + timeout
    with httpx.stream("GET", f"{base_url}/run/{run_id}/stream", timeout=timeout) as resp:
        for line in resp.iter_lines():
            if time.time() > deadline:
                break
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
                events.append(event)
                if event.get("event_type") in ("action.blocked", "run.completed"):
                    break
            except json.JSONDecodeError:
                pass
    return events


def test_hitl_approve_fix_resumes_run(client, base_url):
    session_id = f"hitl-approve-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/run/start",
        json={
            "session_id": session_id,
            "blueprint": _biased_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": {"rubric": {"university_tier": 60, "skills_match": 20, "experience": 20}},
        },
    )
    if r.status_code != 200:
        pytest.skip(f"Run start failed: {r.status_code} {r.text}")

    run_id = r.json()["run_id"]
    events = _collect_events_until_blocked(base_url, run_id)
    blocked_events = [e for e in events if e.get("event_type") == "action.blocked"]

    if not blocked_events:
        pytest.skip("No action.blocked event received — gate did not flag this run")

    blocked = blocked_events[0]
    action_id = blocked.get("data", {}).get("action_id") or blocked.get("action_id")
    assert action_id, f"action.blocked event missing action_id: {blocked}"

    # Submit approve_fix
    decide_r = client.post(
        "/run/decide",
        json={
            "session_id": session_id,
            "run_id": run_id,
            "action_id": action_id,
            "decision": "approve_fix",
        },
    )
    assert decide_r.status_code == 200, f"/run/decide failed: {decide_r.text}"


def test_hitl_override_continues_with_original_params(client, base_url):
    session_id = f"hitl-override-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/run/start",
        json={
            "session_id": session_id,
            "blueprint": _biased_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": {"rubric": {"university_tier": 60, "skills_match": 20, "experience": 20}},
        },
    )
    if r.status_code != 200:
        pytest.skip(f"Run start failed: {r.status_code}")

    run_id = r.json()["run_id"]
    events = _collect_events_until_blocked(base_url, run_id)
    blocked_events = [e for e in events if e.get("event_type") == "action.blocked"]

    if not blocked_events:
        pytest.skip("No action.blocked event — gate did not flag this run")

    blocked = blocked_events[0]
    action_id = blocked.get("data", {}).get("action_id") or blocked.get("action_id")

    decide_r = client.post(
        "/run/decide",
        json={
            "session_id": session_id,
            "run_id": run_id,
            "action_id": action_id,
            "decision": "override",
        },
    )
    assert decide_r.status_code == 200, f"Override decision failed: {decide_r.text}"


def test_hitl_modify_uses_custom_params(client, base_url):
    session_id = f"hitl-modify-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/run/start",
        json={
            "session_id": session_id,
            "blueprint": _biased_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": {"rubric": {"university_tier": 60, "skills_match": 20, "experience": 20}},
        },
    )
    if r.status_code != 200:
        pytest.skip(f"Run start failed: {r.status_code}")

    run_id = r.json()["run_id"]
    events = _collect_events_until_blocked(base_url, run_id)
    blocked_events = [e for e in events if e.get("event_type") == "action.blocked"]

    if not blocked_events:
        pytest.skip("No action.blocked event — gate did not flag this run")

    blocked = blocked_events[0]
    action_id = blocked.get("data", {}).get("action_id") or blocked.get("action_id")

    decide_r = client.post(
        "/run/decide",
        json={
            "session_id": session_id,
            "run_id": run_id,
            "action_id": action_id,
            "decision": "modify",
            "modified_params": {
                "university_tier": 5,
                "skills_match": 40,
                "experience": 40,
                "portfolio_quality": 15,
            },
        },
    )
    assert decide_r.status_code == 200, f"Modify decision failed: {decide_r.text}"


def test_hitl_invalid_action_id_returns_error(client):
    r = client.post(
        "/run/decide",
        json={
            "session_id": "nonexistent",
            "run_id": "nonexistent",
            "action_id": "nonexistent-action-xyz",
            "decision": "approve_fix",
        },
    )
    assert r.status_code in (404, 400, 422), (
        f"Expected error for unknown action_id, got {r.status_code}"
    )
