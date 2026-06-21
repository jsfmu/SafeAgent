"""Suite 6 — Auto-Fix endpoint (POST /fix)."""
import uuid
import pytest
from conftest import BIASED_TOOL_CALL, HIRING_DESCRIPTION


@pytest.fixture(scope="module")
def warn_gate_response(client):
    """Get a real WARN response to use as input for the fix endpoint."""
    import time
    payload = {
        **BIASED_TOOL_CALL,
        "session_id": f"autofix-setup-{uuid.uuid4().hex}",
        "tool_params": {
            "university_tier": 50,
            "years_experience": 15,
            "skills_match": 20,
            "portfolio_quality": 15,
            "_nonce": uuid.uuid4().hex[:6],
        },
    }
    r = client.post("/gate/check", json=payload, timeout=30.0)
    assert r.status_code == 200
    return r.json()


def test_autofix_returns_fixed_params(client, warn_gate_response):
    r = client.post(
        "/fix",
        json={
            "session_id": f"autofix-{uuid.uuid4().hex}",
            "agent_name": BIASED_TOOL_CALL["agent_name"],
            "tool_name": BIASED_TOOL_CALL["tool_name"],
            "original_tool_params": BIASED_TOOL_CALL["tool_params"],
            "builder_intent": HIRING_DESCRIPTION,
            "gate_response": warn_gate_response,
        },
        timeout=30.0,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "fixed_tool_params" in body
    assert isinstance(body["fixed_tool_params"], dict)


def test_autofix_explanation_present(client, warn_gate_response):
    r = client.post(
        "/fix",
        json={
            "session_id": f"autofix-{uuid.uuid4().hex}",
            "agent_name": BIASED_TOOL_CALL["agent_name"],
            "tool_name": BIASED_TOOL_CALL["tool_name"],
            "original_tool_params": BIASED_TOOL_CALL["tool_params"],
            "builder_intent": HIRING_DESCRIPTION,
            "gate_response": warn_gate_response,
        },
        timeout=30.0,
    )
    body = r.json()
    assert isinstance(body.get("explanation"), str) and len(body["explanation"]) > 0
    assert "impact_preview" in body
    assert "fix_type" in body


def test_autofix_preserves_intent(client, warn_gate_response):
    """Fixed params should use the same keys as the original (structure preserved)."""
    r = client.post(
        "/fix",
        json={
            "session_id": f"autofix-{uuid.uuid4().hex}",
            "agent_name": BIASED_TOOL_CALL["agent_name"],
            "tool_name": BIASED_TOOL_CALL["tool_name"],
            "original_tool_params": BIASED_TOOL_CALL["tool_params"],
            "builder_intent": HIRING_DESCRIPTION,
            "gate_response": warn_gate_response,
        },
        timeout=30.0,
    )
    body = r.json()
    fixed = body["fixed_tool_params"]
    original_keys = set(k for k in BIASED_TOOL_CALL["tool_params"] if not k.startswith("_"))
    # Fixed params should contain most original keys (minus any nonce keys)
    overlap = original_keys & set(fixed.keys())
    assert len(overlap) >= len(original_keys) // 2, (
        f"Fixed params missing too many original keys. Fixed: {set(fixed.keys())}, "
        f"Original: {original_keys}"
    )
