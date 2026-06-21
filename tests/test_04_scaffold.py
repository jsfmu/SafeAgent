"""Suite 4 — Blueprint scaffolding endpoint (POST /scaffold)."""
import uuid
import pytest
from conftest import HIRING_DESCRIPTION


@pytest.fixture(scope="module")
def classification(client):
    r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def chosen_topology(client, classification):
    r = client.post(
        "/topology",
        json={"description": HIRING_DESCRIPTION, "classification": classification},
    )
    assert r.status_code == 200
    body = r.json()
    # Pick the recommended topology
    return body["option_a"] if body["option_a"]["recommended"] else body["option_b"]


@pytest.fixture(scope="module")
def scaffold_response(client, classification, chosen_topology):
    session_id = f"test-scaffold-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/scaffold",
        json={
            "description": HIRING_DESCRIPTION,
            "classification": classification,
            "chosen_topology": chosen_topology,
            "session_id": session_id,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_scaffold_returns_blueprint(scaffold_response):
    assert "blueprint" in scaffold_response
    assert "session_id" in scaffold_response


def test_scaffold_agents_present(scaffold_response):
    agents = scaffold_response["blueprint"]["agents"]
    assert len(agents) >= 1
    for agent in agents:
        assert "name" in agent and isinstance(agent["name"], str)
        assert "role" in agent
        assert agent["model"] in ("claude-haiku-4-5-20251001", "claude-sonnet-4-6")
        assert isinstance(agent["tools"], list)
        assert "system_prompt" in agent and len(agent["system_prompt"]) > 10


def test_scaffold_edges_form_valid_graph(scaffold_response):
    bp = scaffold_response["blueprint"]
    agents = {a["name"] for a in bp["agents"]}
    entry = bp["entry_node"]
    assert entry in agents, f"entry_node '{entry}' not in agents {agents}"
    for edge in bp["edges"]:
        assert edge["from_node"] in agents, f"Unknown from_node: {edge['from_node']}"
        assert edge["to_node"] in agents, f"Unknown to_node: {edge['to_node']}"


def test_scaffold_prediction_present(scaffold_response):
    pred = scaffold_response["blueprint"]["prediction"]
    assert pred["cost_usd"] >= 0
    assert pred["latency_sec"] > 0
    assert pred["tokens_in"] > 0
    assert pred["tokens_out"] > 0
    assert pred["confidence"] in ("low", "medium", "high")
    # bottleneck_agent must be a real agent
    agents = {a["name"] for a in scaffold_response["blueprint"]["agents"]}
    assert pred["bottleneck_agent"] in agents


def test_scaffold_topology_field_matches(scaffold_response, chosen_topology):
    assert scaffold_response["blueprint"]["topology"] == chosen_topology["id"]


def test_scaffold_multiturn_edit(client, classification, chosen_topology, scaffold_response):
    """Calling scaffold again with modification_request should update only the requested part."""
    session_id = scaffold_response["session_id"]
    existing_bp = scaffold_response["blueprint"]
    r = client.post(
        "/scaffold",
        json={
            "description": HIRING_DESCRIPTION,
            "classification": classification,
            "chosen_topology": chosen_topology,
            "session_id": session_id,
            "existing_blueprint": existing_bp,
            "modification_request": "Add a Diversity Checker agent after the Scorer.",
        },
    )
    assert r.status_code == 200, r.text
    new_bp = r.json()["blueprint"]
    # Should have at least as many agents as before (or more)
    assert len(new_bp["agents"]) >= len(existing_bp["agents"])
