"""Suite 3 — Topology proposal endpoint (POST /topology)."""
import time
import pytest
from conftest import HIRING_DESCRIPTION


@pytest.fixture(scope="module")
def classification(client):
    r = client.post("/classify", json={"description": HIRING_DESCRIPTION})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def topology_response(client, classification):
    r = client.post(
        "/topology",
        json={"description": HIRING_DESCRIPTION, "classification": classification},
        timeout=60.0,  # extended thinking can take up to 30s
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_topology_returns_two_options(topology_response):
    assert "option_a" in topology_response
    assert "option_b" in topology_response


def test_topology_option_a_is_supervisor(topology_response):
    a = topology_response["option_a"]
    assert a["id"] == "A"
    assert isinstance(a["name"], str) and len(a["name"]) > 0
    assert isinstance(a["description"], str)


def test_topology_option_b_is_react(topology_response):
    b = topology_response["option_b"]
    assert b["id"] == "B"
    assert isinstance(b["name"], str) and len(b["name"]) > 0


def test_topology_tradeoffs_present(topology_response):
    for key in ("option_a", "option_b"):
        opt = topology_response[key]
        assert isinstance(opt["tradeoffs_pro"], list) and len(opt["tradeoffs_pro"]) > 0
        assert isinstance(opt["tradeoffs_con"], list) and len(opt["tradeoffs_con"]) > 0


def test_topology_cost_estimates_are_positive(topology_response):
    for key in ("option_a", "option_b"):
        opt = topology_response[key]
        assert opt["estimated_cost_usd_low"] >= 0
        assert opt["estimated_cost_usd_high"] >= opt["estimated_cost_usd_low"]
        assert opt["estimated_latency_sec"] > 0


def test_exactly_one_option_is_recommended(topology_response):
    recommended = [
        k for k in ("option_a", "option_b")
        if topology_response[k].get("recommended") is True
    ]
    assert len(recommended) == 1, f"Expected exactly 1 recommended option, got {recommended}"


def test_topology_reasoning_chain_present(topology_response):
    for key in ("option_a", "option_b"):
        opt = topology_response[key]
        assert isinstance(opt.get("reasoning_chain"), str) and len(opt["reasoning_chain"]) > 10


def test_topology_thinking_summary_present(topology_response):
    assert isinstance(topology_response.get("thinking_summary"), str)
    assert len(topology_response["thinking_summary"]) > 0
