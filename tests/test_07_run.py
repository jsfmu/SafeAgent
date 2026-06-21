"""Suite 7 — Agent run execution (POST /run/start + GET /run/{run_id}/stream).

Each streaming test starts its own fresh run so they don't compete for events
on the same asyncio.Queue (Queue items are consumed once and gone).
"""
import json
import uuid
import time
import pytest
import httpx
from conftest import HIRING_DESCRIPTION

# Safe (non-biased) rubric so the gate doesn't WARN and block the run mid-stream
SAFE_RUBRIC = {
    "years_relevant_experience": 40,
    "skills_match_to_jd": 35,
    "portfolio_shipped_projects": 15,
    "university_tier": 5,
    "referral_from_employee": 5,
}


def _build_minimal_blueprint():
    """Return a minimal valid blueprint matching the demo hiring scenario."""
    return {
        "topology": "A",
        "topology_name": "Supervisor-Worker",
        "agents": [
            {
                "name": "Parser",
                "role": "Resume parser that extracts structured data from raw text.",
                "model": "claude-haiku-4-5-20251001",
                "tools": ["parse_resume"],
                "system_prompt": "Parse the resume and return structured JSON.",
            },
            {
                "name": "Scorer",
                "role": "Candidate scorer using a fair skills-based rubric.",
                "model": "claude-sonnet-4-6",
                "tools": ["apply_scoring_rubric"],
                "system_prompt": "Score the candidate fairly based on skills and experience.",
            },
            {
                "name": "Email",
                "role": "Email agent that sends the shortlist to the hiring manager.",
                "model": "claude-haiku-4-5-20251001",
                "tools": ["send_email"],
                "system_prompt": "Send a professional email with the ranked candidate shortlist.",
            },
        ],
        "edges": [
            {"from_node": "Parser", "to_node": "Scorer"},
            {"from_node": "Scorer", "to_node": "Email"},
        ],
        "entry_node": "Parser",
        "prediction": {
            "cost_usd": 0.089,
            "latency_sec": 2.3,
            "tokens_in": 1200,
            "tokens_out": 400,
            "bottleneck_agent": "Scorer",
            "confidence": "medium",
        },
    }


def _start_run(client, session_id=None, rubric=None):
    """Helper: start a fresh run and return (run_id, session_id)."""
    session_id = session_id or f"run-test-{uuid.uuid4().hex[:8]}"
    input_data = {
        "resume_text": "Jane Smith, 7 years Python, FastAPI, Redis.",
        "rubric": rubric or SAFE_RUBRIC,
    }
    r = client.post(
        "/run/start",
        json={
            "session_id": session_id,
            "blueprint": _build_minimal_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": input_data,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["run_id"], session_id


def _collect_events(base_url, run_id, timeout=120, stop_on=("run.completed", "run.error")) -> list:
    """Open SSE stream, collect all events until stop_on event or timeout."""
    events = []
    deadline = time.time() + timeout
    with httpx.stream("GET", f"{base_url}/run/{run_id}/stream", timeout=timeout) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if time.time() > deadline:
                break
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
                events.append(event)
                if event.get("event_type") in stop_on:
                    break
            except json.JSONDecodeError:
                pass
    return events


# ── Basic run tests ───────────────────────────────────────────────────────────

def test_run_start_returns_run_id(client):
    run_id, _ = _start_run(client)
    assert isinstance(run_id, str) and len(run_id) > 0


def test_run_stream_receives_events(client, base_url):
    run_id, _ = _start_run(client)
    events = _collect_events(base_url, run_id)
    assert len(events) > 0, "No SSE events received"
    event_types = [e.get("event_type") for e in events]
    assert "run.started" in event_types, f"Missing run.started in {event_types}"


def test_run_stream_has_safety_events(client, base_url):
    """Each tool call emits a safety.scored event (gate runs even when Redis is down)."""
    run_id, _ = _start_run(client)
    events = _collect_events(base_url, run_id)
    safety_events = [e for e in events if e.get("event_type") == "safety.scored"]
    assert len(safety_events) > 0, (
        f"Expected at least one safety.scored event. Got event types: "
        f"{[e.get('event_type') for e in events]}"
    )
    for e in safety_events:
        assert "decision" in e.get("data", e), f"safety.scored missing decision: {e}"


def test_run_stream_contains_node_events(client, base_url):
    """Each agent step should emit node.started and node.completed."""
    run_id, _ = _start_run(client)
    events = _collect_events(base_url, run_id)
    node_events = [e for e in events if e.get("event_type") in ("node.started", "node.completed")]
    assert len(node_events) > 0, (
        f"Expected node.started / node.completed events. Got: "
        f"{[e.get('event_type') for e in events]}"
    )


def test_run_completes_end_to_end(client, base_url):
    """Full run should reach run.completed without error."""
    run_id, _ = _start_run(client)
    events = _collect_events(base_url, run_id)
    event_types = [e.get("event_type") for e in events]
    assert "run.completed" in event_types, (
        f"Run never reached run.completed. Got: {event_types}"
    )
    assert "run.error" not in event_types, (
        f"Run errored unexpectedly: {[e for e in events if e.get('event_type') == 'run.error']}"
    )


def test_run_all_three_agents_execute(client, base_url):
    """Parser, Scorer, and Email nodes should all start and complete."""
    run_id, _ = _start_run(client)
    events = _collect_events(base_url, run_id)
    started = {e.get("agent_name") for e in events if e.get("event_type") == "node.started"}
    completed = {e.get("agent_name") for e in events if e.get("event_type") == "node.completed"}
    for agent in ("Parser", "Scorer", "Email"):
        assert agent in started, f"{agent} never started. Started: {started}"
        assert agent in completed, f"{agent} never completed. Completed: {completed}"


def test_run_invalid_run_id_returns_404(client):
    r = client.get("/run/nonexistent-run-id-xyz/stream", timeout=5.0)
    assert r.status_code == 404
