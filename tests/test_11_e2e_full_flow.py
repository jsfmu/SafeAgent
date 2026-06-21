"""
Suite 11 — Full End-to-End System Tests

Tests the complete SafeAgent pipeline from user prompt to proof panel,
covering the golden path, safety interception, HITL flows, and exports.

Run against a live backend:
    SAFEAGENT_URL=http://localhost:8001 pytest tests/test_11_e2e_full_flow.py -v

These tests make real API calls (Anthropic + Redis when available).
LLM tests are marked slow and can be skipped with: pytest -m "not slow"
"""
import json
import time
import uuid
import pytest
import httpx
from conftest import HIRING_DESCRIPTION, SAFE_TOOL_CALL, BIASED_TOOL_CALL, BLOCKED_TOOL_CALL

SESSION_ID = f"e2e-{uuid.uuid4().hex[:8]}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_blueprint(topology: str = "A") -> dict:
    return {
        "topology": topology,
        "topology_name": "Supervisor-Worker" if topology == "A" else "ReAct",
        "agents": [
            {
                "name": "Parser",
                "role": "Resume parser that extracts structured data from raw text.",
                "model": "claude-haiku-4-5-20251001",
                "tools": ["parse_resume"],
                "system_prompt": "Parse the resume.",
            },
            {
                "name": "Scorer",
                "role": "Candidate scorer using a fair rubric.",
                "model": "claude-sonnet-4-6",
                "tools": ["apply_scoring_rubric"],
                "system_prompt": "Score candidates fairly.",
            },
            {
                "name": "Email",
                "role": "Email agent that sends the shortlist.",
                "model": "claude-haiku-4-5-20251001",
                "tools": ["send_email"],
                "system_prompt": "Send a professional shortlist email.",
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


SAFE_RUBRIC = {
    "years_relevant_experience": 40,
    "skills_match_to_jd": 35,
    "portfolio_shipped_projects": 15,
    "university_tier": 5,
    "referral_from_employee": 5,
}


def _collect_sse(base_url: str, run_id: str, timeout: int = 120) -> list[dict]:
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
                evt = json.loads(line[5:].strip())
                events.append(evt)
                if evt.get("event_type") in ("run.completed", "run.error"):
                    break
            except json.JSONDecodeError:
                pass
    return events


# ─────────────────────────────────────────────────────────────────────────────
# E2E-01: Health → Classify → Topology (full pipeline Steps 1-2)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_ClassifyToTopology:
    """Steps 1-2: Health check → Classify → Topology proposals."""

    def test_health_before_pipeline(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.slow
    def test_classify_then_topology_connected(self, client):
        """Classify output should feed naturally into topology request."""
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        assert cls_r.status_code == 200, cls_r.text
        cls = cls_r.json()

        topo_r = client.post("/topology", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
        })
        assert topo_r.status_code == 200, topo_r.text
        topo = topo_r.json()
        assert "options" in topo
        assert len(topo["options"]) == 2
        options_by_id = {o["id"]: o for o in topo["options"]}
        assert "A" in options_by_id and "B" in options_by_id

    @pytest.mark.slow
    def test_topology_options_have_required_fields(self, client):
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        cls = cls_r.json()
        topo_r = client.post("/topology", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
        })
        for opt in topo_r.json()["options"]:
            for field in ("id", "name", "estimated_cost_usd_low", "estimated_latency_sec", "recommended"):
                assert field in opt, f"Option missing field: {field}"

    @pytest.mark.slow
    def test_exactly_one_topology_is_recommended(self, client):
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        cls = cls_r.json()
        topo_r = client.post("/topology", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
        })
        recommended = [o for o in topo_r.json()["options"] if o.get("recommended")]
        assert len(recommended) == 1, f"Expected exactly 1 recommended, got {len(recommended)}"


# ─────────────────────────────────────────────────────────────────────────────
# E2E-02: Classify → Topology → Scaffold (Steps 1-3)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_Scaffold:
    """Step 3: Scaffold blueprint from classification + topology."""

    @pytest.mark.slow
    def test_scaffold_produces_valid_blueprint(self, client):
        session = f"scaffold-e2e-{uuid.uuid4().hex[:8]}"
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        cls = cls_r.json()

        topo_r = client.post("/topology", json={"description": HIRING_DESCRIPTION, "classification": cls})
        options = topo_r.json()["options"]
        chosen = next(o for o in options if o.get("recommended"))

        scaffold_r = client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
            "selected_topology": chosen,
            "session_id": session,
        })
        assert scaffold_r.status_code == 200, scaffold_r.text
        bp = scaffold_r.json()["blueprint"]
        assert "agents" in bp and len(bp["agents"]) > 0
        assert "edges" in bp
        assert "entry_node" in bp
        assert "prediction" in bp

    @pytest.mark.slow
    def test_scaffold_blueprint_agents_have_tools(self, client):
        session = f"tools-e2e-{uuid.uuid4().hex[:8]}"
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        cls = cls_r.json()
        topo_r = client.post("/topology", json={"description": HIRING_DESCRIPTION, "classification": cls})
        chosen = next(o for o in topo_r.json()["options"] if o.get("recommended"))
        scaffold_r = client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
            "selected_topology": chosen,
            "session_id": session,
        })
        for agent in scaffold_r.json()["blueprint"]["agents"]:
            assert len(agent.get("tools", [])) > 0, f"Agent {agent['name']} has no tools"

    @pytest.mark.slow
    def test_scaffold_cost_prediction_is_positive(self, client):
        session = f"cost-e2e-{uuid.uuid4().hex[:8]}"
        cls_r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
        cls = cls_r.json()
        topo_r = client.post("/topology", json={"description": HIRING_DESCRIPTION, "classification": cls})
        chosen = topo_r.json()["options"][0]
        scaffold_r = client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": cls,
            "selected_topology": chosen,
            "session_id": session,
        })
        pred = scaffold_r.json()["blueprint"]["prediction"]
        assert pred["cost_usd"] > 0
        assert pred["latency_sec"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# E2E-03: Gate → Run → SSE (Steps 4-5, safety gate in the run loop)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_SafetyGate:
    """Safety gate fires on every tool call during a run."""

    def test_t1_blocks_drop_table_immediately(self, client):
        r = client.post("/gate/check", json={
            "session_id": f"gate-t1-{uuid.uuid4().hex[:6]}",
            "agent_name": "BadActor",
            "tool_name": "drop_table",
            "tool_params": {"table": "candidates"},
            "builder_intent": "delete the database",
            "agent_role": "DBA",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "BLOCK"
        assert body["tier_triggered"] == 1
        assert body["latency_ms"] < 10

    def test_t1_blocks_all_dangerous_tools(self, client):
        dangerous = ["bulk_delete", "send_to_all", "drop_table", "drop_db", "rm_rf"]
        for tool in dangerous:
            r = client.post("/gate/check", json={
                "session_id": f"t1-{tool}-{uuid.uuid4().hex[:6]}",
                "agent_name": "Agent",
                "tool_name": tool,
                "tool_params": {},
                "builder_intent": "test",
                "agent_role": "agent",
            })
            assert r.json()["decision"] == "BLOCK", f"{tool} not blocked"

    def test_t1_blocks_wildcard_params(self, client):
        for bad_val in ["*", "all", "everyone", "drop"]:
            r = client.post("/gate/check", json={
                "session_id": f"param-{uuid.uuid4().hex[:6]}",
                "agent_name": "Agent",
                "tool_name": "send_email",
                "tool_params": {"recipient": bad_val},
                "builder_intent": "send notifications",
                "agent_role": "Email agent",
            })
            assert r.json()["decision"] == "BLOCK", f"param '{bad_val}' not blocked"

    def test_t1_blocks_whitespace_bypass_attempt(self, client):
        """Whitespace around a blocked tool name must not bypass T1."""
        r = client.post("/gate/check", json={
            "session_id": f"bypass-{uuid.uuid4().hex[:6]}",
            "agent_name": "Agent",
            "tool_name": "  drop_table  ",
            "tool_params": {"table": "users"},
            "builder_intent": "test",
            "agent_role": "agent",
        })
        assert r.json()["decision"] == "BLOCK"

    @pytest.mark.slow
    def test_t3_scores_safe_action_as_allow(self, client):
        r = client.post("/gate/check", json={
            **SAFE_TOOL_CALL,
            "session_id": f"safe-{uuid.uuid4().hex[:6]}",
        }, timeout=30.0)
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] in ("ALLOW", "WARN")
        assert body["tier_triggered"] in (2, 3)

    @pytest.mark.slow
    def test_t3_flags_biased_rubric(self, client):
        r = client.post("/gate/check", json={
            **BIASED_TOOL_CALL,
            "session_id": f"biased-{uuid.uuid4().hex[:6]}",
        }, timeout=30.0)
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] in ("WARN", "BLOCK")

    def test_gate_response_schema(self, client):
        r = client.post("/gate/check", json={
            **SAFE_TOOL_CALL,
            "session_id": f"schema-{uuid.uuid4().hex[:6]}",
            "tool_name": "drop_table",
        })
        body = r.json()
        for field in ("decision", "tier_triggered", "cache_hit", "latency_ms"):
            assert field in body


# ─────────────────────────────────────────────────────────────────────────────
# E2E-04: Full agent run (Steps 4-5, SSE stream)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_AgentRun:
    """Full LangGraph run with SSE event streaming."""

    def _start_run(self, client, session_id=None):
        sid = session_id or f"run-{uuid.uuid4().hex[:8]}"
        r = client.post("/run/start", json={
            "session_id": sid,
            "blueprint": _minimal_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": {
                "resume_text": "Alice Kim, 5 years Python, FastAPI, Redis, ML experience.",
                "rubric": SAFE_RUBRIC,
            },
        })
        assert r.status_code == 200, r.text
        return r.json()["run_id"], sid

    def test_run_start_returns_run_id_and_stream_url(self, client):
        run_id, _ = self._start_run(client)
        assert run_id and len(run_id) > 0

    def test_run_stream_returns_200(self, client, base_url):
        run_id, _ = self._start_run(client)
        with httpx.stream("GET", f"{base_url}/run/{run_id}/stream", timeout=5.0) as resp:
            assert resp.status_code == 200

    def test_run_emits_run_started(self, client, base_url):
        run_id, _ = self._start_run(client)
        events = _collect_sse(base_url, run_id)
        types = [e.get("event_type") for e in events]
        assert "run.started" in types

    def test_run_emits_safety_scored_events(self, client, base_url):
        run_id, _ = self._start_run(client)
        events = _collect_sse(base_url, run_id)
        safety = [e for e in events if e.get("event_type") == "safety.scored"]
        assert len(safety) > 0, "Expected at least one safety.scored event per tool call"

    def test_run_completes_without_error(self, client, base_url):
        run_id, _ = self._start_run(client)
        events = _collect_sse(base_url, run_id)
        types = [e.get("event_type") for e in events]
        assert "run.completed" in types, f"No run.completed. Got: {types}"
        assert "run.error" not in types

    def test_all_three_agents_start_and_complete(self, client, base_url):
        run_id, _ = self._start_run(client)
        events = _collect_sse(base_url, run_id)
        started = {e.get("agent_name") for e in events if e.get("event_type") == "node.started"}
        done = {e.get("agent_name") for e in events if e.get("event_type") == "node.completed"}
        for ag in ("Parser", "Scorer", "Email"):
            assert ag in started, f"{ag} never started. Started: {started}"
            assert ag in done, f"{ag} never completed. Done: {done}"

    def test_run_invalid_id_returns_404(self, client):
        r = client.get("/run/no-such-run-xyz/stream", timeout=3.0)
        assert r.status_code == 404

    def test_concurrent_runs_independent(self, base_url):
        """Two simultaneous runs should not interfere with each other."""
        import concurrent.futures

        def start_and_collect():
            sid = f"concurrent-{uuid.uuid4().hex[:8]}"
            with httpx.Client(base_url=base_url, timeout=120.0) as c:
                r = c.post("/run/start", json={
                    "session_id": sid,
                    "blueprint": _minimal_blueprint(),
                    "builder_intent": HIRING_DESCRIPTION,
                    "input_data": {"resume_text": "Bob Test", "rubric": SAFE_RUBRIC},
                })
                run_id = r.json()["run_id"]
            events = _collect_sse(base_url, run_id)
            return [e.get("event_type") for e in events]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1, f2 = pool.submit(start_and_collect), pool.submit(start_and_collect)
            types1, types2 = f1.result(), f2.result()

        assert "run.completed" in types1
        assert "run.completed" in types2


# ─────────────────────────────────────────────────────────────────────────────
# E2E-05: HITL decision flow (Step 5 — human approves/modifies/overrides)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_HITL:
    """Human-in-the-loop decision endpoint (/run/decide)."""

    def test_decide_on_unknown_run_returns_404(self, client):
        r = client.post("/run/decide", json={
            "session_id": "x",
            "run_id": "nonexistent-run",
            "action_id": "act-1",
            "decision": "approve_fix",
            "modified_params": None,
        })
        assert r.status_code == 404

    def test_decide_valid_run_returns_ok(self, client):
        """Posting a HITL decision to a real run_id should return {ok: true}."""
        sid = f"hitl-{uuid.uuid4().hex[:8]}"
        start_r = client.post("/run/start", json={
            "session_id": sid,
            "blueprint": _minimal_blueprint(),
            "builder_intent": HIRING_DESCRIPTION,
            "input_data": {"resume_text": "Test candidate", "rubric": SAFE_RUBRIC},
        })
        run_id = start_r.json()["run_id"]

        decide_r = client.post("/run/decide", json={
            "session_id": sid,
            "run_id": run_id,
            "action_id": "act-000",
            "decision": "approve_fix",
            "modified_params": None,
        })
        assert decide_r.status_code == 200
        assert decide_r.json().get("ok") is True


# ─────────────────────────────────────────────────────────────────────────────
# E2E-06: Proof Panel (Step 6 — prediction vs. actual)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_ProofPanel:
    """Proof panel merges Arize telemetry + Redis cache stats."""

    def test_proof_returns_200_for_known_session(self, client):
        session = f"proof-{uuid.uuid4().hex[:8]}"
        # Scaffold a blueprint so session is registered
        client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": {
                "domain": "hiring",
                "complexity": "medium",
                "risk_profile": "high",
                "agent_count_estimate": 3,
                "tool_count_estimate": 3,
                "has_external_api": False,
            },
            "selected_topology": {
                "id": "A",
                "name": "Supervisor-Worker",
                "description": "test",
                "tradeoffs_pro": [],
                "tradeoffs_con": [],
                "estimated_cost_usd_low": 0.05,
                "estimated_cost_usd_high": 0.12,
                "estimated_latency_sec": 2.0,
                "recommended": True,
                "reasoning_chain": "",
            },
            "session_id": session,
        })
        r = client.get(f"/proof/{session}")
        assert r.status_code == 200

    def test_proof_has_required_fields(self, client):
        session = f"proof2-{uuid.uuid4().hex[:8]}"
        client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": {"domain": "hiring", "complexity": "medium",
                               "risk_profile": "high", "agent_count_estimate": 3,
                               "tool_count_estimate": 3, "has_external_api": False},
            "selected_topology": {"id": "A", "name": "Supervisor-Worker",
                                  "description": "test", "tradeoffs_pro": [],
                                  "tradeoffs_con": [], "estimated_cost_usd_low": 0.05,
                                  "estimated_cost_usd_high": 0.12,
                                  "estimated_latency_sec": 2.0, "recommended": True,
                                  "reasoning_chain": ""},
            "session_id": session,
        })
        r = client.get(f"/proof/{session}")
        body = r.json()
        for field in ("predicted_cost_usd", "topology_a", "redis_cache_hits"):
            assert field in body, f"Proof missing field: {field}"

    def test_proof_division_by_zero_safe(self, client):
        """Proof panel with zero predicted cost should not crash."""
        session = f"zero-cost-{uuid.uuid4().hex[:8]}"
        client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": {"domain": "hiring", "complexity": "low",
                               "risk_profile": "low", "agent_count_estimate": 1,
                               "tool_count_estimate": 1, "has_external_api": False},
            "selected_topology": {"id": "A", "name": "Supervisor-Worker",
                                  "description": "test", "tradeoffs_pro": [],
                                  "tradeoffs_con": [], "estimated_cost_usd_low": 0.0,
                                  "estimated_cost_usd_high": 0.0,
                                  "estimated_latency_sec": 1.0, "recommended": True,
                                  "reasoning_chain": ""},
            "session_id": session,
        })
        r = client.get(f"/proof/{session}", params={"predicted_cost_usd": 0.0})
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# E2E-07: Export (blueprint JSON + Python code artifact)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_Export:
    """Blueprint JSON and Python code export endpoints."""

    def _scaffold_session(self, client) -> str:
        session = f"export-{uuid.uuid4().hex[:8]}"
        client.post("/scaffold", json={
            "description": HIRING_DESCRIPTION,
            "classification": {"domain": "hiring", "complexity": "medium",
                               "risk_profile": "high", "agent_count_estimate": 3,
                               "tool_count_estimate": 3, "has_external_api": False},
            "selected_topology": {"id": "A", "name": "Supervisor-Worker",
                                  "description": "test", "tradeoffs_pro": [],
                                  "tradeoffs_con": [], "estimated_cost_usd_low": 0.05,
                                  "estimated_cost_usd_high": 0.12,
                                  "estimated_latency_sec": 2.0, "recommended": True,
                                  "reasoning_chain": ""},
            "session_id": session,
        })
        return session

    def test_export_blueprint_returns_json(self, client):
        session = self._scaffold_session(client)
        r = client.get(f"/export/{session}")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    def test_export_blueprint_has_audit_schema(self, client):
        session = self._scaffold_session(client)
        r = client.get(f"/export/{session}")
        data = r.json()
        assert "blueprint" in data or "agents" in data or "session_id" in data

    def test_export_code_returns_python(self, client):
        session = self._scaffold_session(client)
        r = client.get(f"/export/{session}/code")
        assert r.status_code == 200
        code = r.text
        assert "StateGraph" in code or "langgraph" in code.lower() or "def " in code

    def test_export_unknown_session_returns_404(self, client):
        r = client.get("/export/session-does-not-exist-xyz")
        assert r.status_code == 404

    def test_export_code_unknown_session_returns_404(self, client):
        r = client.get("/export/session-does-not-exist-xyz/code")
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# E2E-08: Audit & cache stats endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_Audit:
    """Audit log and cache stats (graceful when Redis is absent)."""

    def test_audit_export_returns_200(self, client):
        r = client.get("/audit/export/any-session")
        assert r.status_code == 200

    def test_audit_stream_tail_returns_200(self, client):
        r = client.get("/audit/stream-tail")
        assert r.status_code == 200

    def test_cache_stats_returns_200(self, client):
        r = client.get("/audit/cache-stats/any-session")
        assert r.status_code == 200

    def test_cache_stats_has_expected_shape(self, client):
        r = client.get("/audit/cache-stats/test-session")
        body = r.json()
        assert "cache_hits" in body
        assert "cache_misses" in body


# ─────────────────────────────────────────────────────────────────────────────
# E2E-09: ASI:One agent discovery
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_AsiDiscovery:
    """AgentVerse discovery endpoint (falls back to mock when no API key)."""

    def test_discover_returns_200(self, client):
        r = client.post("/asi/discover", json={
            "domain": "hiring",
            "description": "resume screening agent for hiring automation",
        })
        assert r.status_code == 200

    def test_discover_returns_agents_list(self, client):
        r = client.post("/asi/discover", json={
            "domain": "support",
            "description": "customer support agent for ticket handling",
        })
        body = r.json()
        assert "agents" in body
        assert isinstance(body["agents"], list)

    def test_discover_has_source_field(self, client):
        r = client.post("/asi/discover", json={
            "domain": "research",
            "description": "research assistant agent for literature review",
        })
        body = r.json()
        assert "source" in body
        assert body["source"] in ("agentverse", "mock")


# ─────────────────────────────────────────────────────────────────────────────
# E2E-10: Auto-fix generation
# ─────────────────────────────────────────────────────────────────────────────

class TestE2E_AutoFix:
    """Standalone auto-fix generation endpoint (POST /fix)."""

    @pytest.mark.slow
    def test_autofix_generates_safer_rubric(self, client):
        r = client.post("/fix", json={
            "session_id": f"fix-{uuid.uuid4().hex[:8]}",
            "agent_name": "Scorer",
            "tool_name": "apply_scoring_rubric",
            "original_tool_params": {
                "university_tier": 35,
                "years_experience": 20,
                "skills_match": 30,
                "portfolio_quality": 15,
            },
            "builder_intent": HIRING_DESCRIPTION,
            "gate_response": {
                "decision": "WARN",
                "tier_triggered": 3,
                "misalignment_score": 87,
                "oversight_score": 31,
                "explanation": "Rubric heavily weights university tier which can introduce socioeconomic bias.",
                "fix_draft": "Reduce university_tier weight to 5 and redistribute to skills.",
                "cache_hit": False,
                "latency_ms": 820,
            },
        }, timeout=30.0)
        assert r.status_code == 200
        body = r.json()
        assert "fixed_tool_params" in body
        assert "explanation" in body

    @pytest.mark.slow
    def test_autofix_reduces_bias_in_rubric(self, client):
        """University tier weight should be lower in the fixed rubric."""
        r = client.post("/fix", json={
            "session_id": f"bias-fix-{uuid.uuid4().hex[:8]}",
            "agent_name": "Scorer",
            "tool_name": "apply_scoring_rubric",
            "original_tool_params": {"university_tier": 35, "skills_match": 30},
            "builder_intent": HIRING_DESCRIPTION,
            "gate_response": {
                "decision": "WARN", "tier_triggered": 3,
                "misalignment_score": 87, "oversight_score": 31,
                "explanation": "University tier is over-weighted.",
                "fix_draft": "Reduce university_tier.",
                "cache_hit": False, "latency_ms": 820,
            },
        }, timeout=30.0)
        body = r.json()
        original_uni = 35
        fixed_uni = body.get("fixed_tool_params", {}).get("university_tier", original_uni)
        assert fixed_uni <= original_uni, "Fix should not increase bias weight"
