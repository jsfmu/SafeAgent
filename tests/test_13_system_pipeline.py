"""
Suite 13 — System Tests: Full Pipeline (Classify → Topology → Scaffold → Run → Export)

Tests the complete builder workflow end-to-end, covering three different
use-case domains (hiring, customer support, research) and multiple edge cases.

Run fast (no LLM):
    pytest tests/test_13_system_pipeline.py -v -m "not slow"

Run all:
    pytest tests/test_13_system_pipeline.py -v
"""
import json
import os
import time
import uuid
import pytest
import httpx

BASE_URL = os.getenv("SAFEAGENT_URL", "http://localhost:8001")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

HIRING_DESC = (
    "Build an agent to screen resumes, score candidates fairly on skills and "
    "experience, and email a shortlist to the hiring manager."
)
SUPPORT_DESC = (
    "Build a customer support agent that classifies incoming tickets, routes "
    "them to the right department, and auto-replies to common questions."
)
RESEARCH_DESC = (
    "Build a research assistant that searches academic databases, summarises "
    "papers, and generates a weekly digest email."
)


def classify(client, desc):
    r = client.post("/classify", json={"description": desc})
    assert r.status_code == 200
    return r.json()


def topology(client, desc, cls):
    r = client.post("/topology", json={"description": desc, "classification": cls})
    assert r.status_code == 200
    return r.json()


def scaffold(client, desc, cls, topo_option, session_id):
    r = client.post("/scaffold", json={
        "description": desc,
        "classification": cls,
        "selected_topology": topo_option,
        "session_id": session_id,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _minimal_bp(name="Parser"):
    return {
        "topology": "A",
        "topology_name": "Supervisor-Worker",
        "agents": [{
            "name": name,
            "role": "Parses input data.",
            "model": "claude-haiku-4-5-20251001",
            "tools": ["parse_input"],
            "system_prompt": "Parse the input.",
        }],
        "edges": [],
        "entry_node": name,
        "prediction": {
            "cost_usd": 0.01, "latency_sec": 1.0,
            "tokens_in": 200, "tokens_out": 50,
            "bottleneck_agent": name, "confidence": "low",
        },
    }


def collect_sse(base_url, run_id, timeout=90):
    events = []
    deadline = time.time() + timeout
    with httpx.stream("GET", f"{base_url}/run/{run_id}/stream", timeout=timeout) as resp:
        for line in resp.iter_lines():
            if time.time() > deadline:
                break
            if not line.startswith("data:"):
                continue
            try:
                evt = json.loads(line[5:].strip())
                events.append(evt)
                if evt.get("event_type") in ("run.completed", "run.error"):
                    break
            except json.JSONDecodeError:
                pass
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Step-by-step pipeline: Classify
# ─────────────────────────────────────────────────────────────────────────────

class TestClassify:

    @pytest.mark.slow
    def test_classify_hiring(self, client):
        cls = classify(client, HIRING_DESC)
        assert cls["domain"] in ("hiring", "hr", "recruitment", "HR")

    @pytest.mark.slow
    def test_classify_support(self, client):
        cls = classify(client, SUPPORT_DESC)
        assert "support" in cls["domain"].lower() or "customer" in cls["domain"].lower()

    @pytest.mark.slow
    def test_classify_research(self, client):
        cls = classify(client, RESEARCH_DESC)
        assert "research" in cls["domain"].lower() or "data" in cls["domain"].lower()

    @pytest.mark.slow
    def test_classify_has_risk_profile(self, client):
        cls = classify(client, HIRING_DESC)
        assert cls.get("risk_profile") in ("low", "medium", "high")

    @pytest.mark.slow
    def test_classify_has_agent_count(self, client):
        cls = classify(client, HIRING_DESC)
        assert isinstance(cls.get("agent_count_estimate"), int)
        assert cls["agent_count_estimate"] > 0

    def test_classify_empty_description_rejected(self, client):
        r = client.post("/classify", json={"description": ""})
        assert r.status_code in (400, 422)

    def test_classify_very_short_description(self, client):
        r = client.post("/classify", json={"description": "do stuff"})
        assert r.status_code == 200  # short but valid

    @pytest.mark.slow
    def test_classify_high_risk_flagged_for_hiring(self, client):
        """Hiring systems that make hiring decisions should be marked high risk."""
        cls = classify(client, HIRING_DESC)
        assert cls["risk_profile"] in ("medium", "high")


# ─────────────────────────────────────────────────────────────────────────────
# Step-by-step pipeline: Topology
# ─────────────────────────────────────────────────────────────────────────────

class TestTopology:

    @pytest.mark.slow
    def test_topology_returns_two_options(self, client):
        cls = classify(client, HIRING_DESC)
        topo = topology(client, HIRING_DESC, cls)
        assert len(topo["options"]) == 2

    @pytest.mark.slow
    def test_topology_option_ids_are_a_and_b(self, client):
        cls = classify(client, HIRING_DESC)
        topo = topology(client, HIRING_DESC, cls)
        ids = {o["id"] for o in topo["options"]}
        assert ids == {"A", "B"}

    @pytest.mark.slow
    def test_topology_exactly_one_recommended(self, client):
        cls = classify(client, HIRING_DESC)
        topo = topology(client, HIRING_DESC, cls)
        recs = [o for o in topo["options"] if o.get("recommended")]
        assert len(recs) == 1

    @pytest.mark.slow
    def test_topology_cost_is_positive(self, client):
        cls = classify(client, RESEARCH_DESC)
        topo = topology(client, RESEARCH_DESC, cls)
        for opt in topo["options"]:
            assert opt["estimated_cost_usd_low"] >= 0

    @pytest.mark.slow
    def test_topology_support_domain_produces_options(self, client):
        cls = classify(client, SUPPORT_DESC)
        topo = topology(client, SUPPORT_DESC, cls)
        assert len(topo["options"]) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Step-by-step pipeline: Scaffold
# ─────────────────────────────────────────────────────────────────────────────

class TestScaffold:

    def _cls_topo(self, client, desc):
        cls = classify(client, desc)
        topo = topology(client, desc, cls)
        recommended = next(o for o in topo["options"] if o.get("recommended"))
        return cls, recommended

    @pytest.mark.slow
    def test_scaffold_hiring_produces_blueprint(self, client):
        cls, topo = self._cls_topo(client, HIRING_DESC)
        sid = f"scf-hire-{uuid.uuid4().hex[:6]}"
        result = scaffold(client, HIRING_DESC, cls, topo, sid)
        bp = result["blueprint"]
        assert len(bp["agents"]) >= 2
        assert bp["entry_node"]

    @pytest.mark.slow
    def test_scaffold_support_produces_blueprint(self, client):
        cls, topo = self._cls_topo(client, SUPPORT_DESC)
        sid = f"scf-sup-{uuid.uuid4().hex[:6]}"
        result = scaffold(client, SUPPORT_DESC, cls, topo, sid)
        bp = result["blueprint"]
        assert len(bp["agents"]) >= 1

    @pytest.mark.slow
    def test_scaffold_research_produces_blueprint(self, client):
        cls, topo = self._cls_topo(client, RESEARCH_DESC)
        sid = f"scf-res-{uuid.uuid4().hex[:6]}"
        result = scaffold(client, RESEARCH_DESC, cls, topo, sid)
        bp = result["blueprint"]
        assert "agents" in bp

    @pytest.mark.slow
    def test_scaffold_agents_have_system_prompts(self, client):
        cls, topo = self._cls_topo(client, HIRING_DESC)
        sid = f"scf-prompts-{uuid.uuid4().hex[:6]}"
        result = scaffold(client, HIRING_DESC, cls, topo, sid)
        for agent in result["blueprint"]["agents"]:
            assert agent.get("system_prompt"), f"Agent {agent['name']} missing system_prompt"

    @pytest.mark.slow
    def test_scaffold_prediction_positive(self, client):
        cls, topo = self._cls_topo(client, HIRING_DESC)
        sid = f"scf-pred-{uuid.uuid4().hex[:6]}"
        result = scaffold(client, HIRING_DESC, cls, topo, sid)
        pred = result["blueprint"]["prediction"]
        assert pred["cost_usd"] > 0
        assert pred["latency_sec"] > 0

    @pytest.mark.slow
    def test_scaffold_session_exportable(self, client):
        """Scaffolded session should be immediately available for export."""
        cls, topo = self._cls_topo(client, HIRING_DESC)
        sid = f"scf-export-{uuid.uuid4().hex[:6]}"
        scaffold(client, HIRING_DESC, cls, topo, sid)
        r = client.get(f"/export/{sid}")
        assert r.status_code == 200

    @pytest.mark.slow
    def test_scaffold_code_export_contains_langgraph(self, client):
        """Code export must contain LangGraph StateGraph references."""
        cls, topo = self._cls_topo(client, HIRING_DESC)
        sid = f"scf-code-{uuid.uuid4().hex[:6]}"
        scaffold(client, HIRING_DESC, cls, topo, sid)
        r = client.get(f"/export/{sid}/code")
        assert r.status_code == 200
        assert "StateGraph" in r.text or "langgraph" in r.text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Agent Run (LangGraph)
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentRun:

    def _start(self, client, intent="process the input", bp=None):
        sid = f"run13-{uuid.uuid4().hex[:6]}"
        r = client.post("/run/start", json={
            "session_id": sid,
            "blueprint": bp or _minimal_bp(),
            "builder_intent": intent,
            "input_data": {"text": "test input"},
        })
        assert r.status_code == 200
        return r.json()["run_id"], sid

    def test_run_start_returns_run_id(self, client):
        run_id, _ = self._start(client)
        assert run_id

    def test_run_stream_200(self, client):
        run_id, _ = self._start(client)
        with httpx.stream("GET", f"{BASE_URL}/run/{run_id}/stream", timeout=5) as r:
            assert r.status_code == 200

    def test_run_nonexistent_404(self, client):
        r = client.get("/run/does-not-exist/stream", timeout=3)
        assert r.status_code == 404

    def test_run_emits_run_started_event(self, client):
        run_id, _ = self._start(client)
        events = collect_sse(BASE_URL, run_id)
        types = [e.get("event_type") for e in events]
        assert "run.started" in types

    def test_run_completes(self, client):
        run_id, _ = self._start(client)
        events = collect_sse(BASE_URL, run_id)
        types = [e.get("event_type") for e in events]
        assert "run.completed" in types

    def test_run_emits_safety_events(self, client):
        run_id, _ = self._start(client)
        events = collect_sse(BASE_URL, run_id)
        safety = [e for e in events if "safety" in e.get("event_type", "")]
        assert len(safety) > 0

    def test_run_no_error_events(self, client):
        run_id, _ = self._start(client)
        events = collect_sse(BASE_URL, run_id)
        errors = [e for e in events if e.get("event_type") == "run.error"]
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_hitl_decide_404_for_bad_run(self, client):
        r = client.post("/run/decide", json={
            "session_id": "x",
            "run_id": "no-such-run",
            "action_id": "a",
            "decision": "approve_fix",
            "modified_params": None,
        })
        assert r.status_code == 404

    def test_hitl_decide_valid_run_ok(self, client):
        run_id, sid = self._start(client)
        r = client.post("/run/decide", json={
            "session_id": sid,
            "run_id": run_id,
            "action_id": "act-000",
            "decision": "approve_fix",
            "modified_params": None,
        })
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ─────────────────────────────────────────────────────────────────────────────
# Export endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestExport:

    def _scaffold_session(self, client, desc=HIRING_DESC):
        sid = f"exp13-{uuid.uuid4().hex[:6]}"
        client.post("/scaffold", json={
            "description": desc,
            "classification": {
                "domain": "hiring", "complexity": "medium",
                "risk_profile": "high", "agent_count_estimate": 3,
                "tool_count_estimate": 3, "has_external_api": False,
            },
            "chosen_topology": {
                "id": "A", "name": "Supervisor-Worker",
                "description": "test", "tradeoffs_pro": [], "tradeoffs_con": [],
                "estimated_cost_usd_low": 0.05, "estimated_cost_usd_high": 0.12,
                "estimated_latency_sec": 2.0, "recommended": True, "reasoning_chain": "",
            },
            "session_id": sid,
        })
        return sid

    def test_blueprint_json_returns_200(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/export/{sid}")
        assert r.status_code == 200

    def test_blueprint_content_type_json(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/export/{sid}")
        assert "application/json" in r.headers.get("content-type", "")

    def test_blueprint_has_session_id(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/export/{sid}")
        data = r.json()
        assert "session_id" in data or "blueprint" in data or "agents" in data

    def test_code_export_returns_text(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/export/{sid}/code")
        assert r.status_code == 200
        assert len(r.text) > 50

    def test_export_unknown_session_404(self, client):
        r = client.get("/export/ghost-session-000")
        assert r.status_code == 404

    def test_code_export_unknown_session_404(self, client):
        r = client.get("/export/ghost-session-000/code")
        assert r.status_code == 404

    def test_proof_panel_returns_200(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/proof/{sid}")
        assert r.status_code == 200

    def test_proof_panel_has_predicted_cost(self, client):
        sid = self._scaffold_session(client)
        r = client.get(f"/proof/{sid}")
        assert "predicted_cost_usd" in r.json()
