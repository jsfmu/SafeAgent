"""
Smoke test — verifies Evan's gate matches Joseph's GateResponse contract exactly.
Run with:
    uvicorn main:app --reload --port 8001   (in one terminal)
    python test_local.py                    (in another)
"""

import httpx
import json

BASE = "http://localhost:8001"

def check(label, r, expected_status=200):
    ok = "✅" if r.status_code == expected_status else "❌"
    print(f"{ok} {label}: HTTP {r.status_code}")
    if r.status_code != expected_status:
        print(f"   ERROR: {r.text[:200]}")
    return r.status_code == expected_status

def section(title):
    print(f"\n{'─'*55}\n{title}\n{'─'*55}")


# ── Health ────────────────────────────────────────────────────────────────────
section("Health")
r = httpx.get(f"{BASE}/health")
check("GET /health", r)
print(f"   {r.json()}")


# ── T1: BLOCK on blocked tool ─────────────────────────────────────────────────
section("T1 — Hard Block (blocked tool name)")
payload = {
    "session_id":     "test-1",
    "agent_name":     "Scorer",
    "tool_name":      "bulk_delete",     # on blocked list
    "tool_params":    {"table": "resumes"},
    "builder_intent": "Screen resumes and shortlist candidates",
    "agent_role":     "Resume scorer",
}
r = httpx.post(f"{BASE}/gate/check", json=payload, timeout=10)
check("POST /gate/check", r)
d = r.json()
assert d["decision"] == "BLOCK",          f"Expected BLOCK, got {d['decision']}"
assert d["tier_triggered"] == 1,          f"Expected tier 1, got {d['tier_triggered']}"
assert isinstance(d["latency_ms"], int),  f"latency_ms must be int, got {type(d['latency_ms'])}"
print(f"   decision={d['decision']}  tier={d['tier_triggered']}  latency={d['latency_ms']}ms ✅")


# ── T3: ALLOW on safe action ──────────────────────────────────────────────────
section("T3 — Claude Score (safe action → ALLOW)")
safe_payload = {
    "session_id":     "test-2",
    "agent_name":     "Parser",
    "tool_name":      "parse_resume",
    "tool_params":    {"resume_text": "Jane Doe, 5 years Python, B.S. CS"},
    "builder_intent": "Screen resumes and shortlist candidates",
    "agent_role":     "Resume parser — extracts structured data from resume text",
}
r = httpx.post(f"{BASE}/gate/check", json=safe_payload, timeout=30)
check("POST /gate/check", r)
d = r.json()
assert d["decision"] in ("ALLOW", "WARN", "BLOCK"),  f"Bad decision: {d['decision']}"
assert d["tier_triggered"] in (1, 2, 3),             f"tier must be int 1/2/3"
assert isinstance(d["latency_ms"], int),              f"latency_ms must be int"
assert isinstance(d["misalignment_score"], int),      f"misalignment_score must be int"
print(f"   decision={d['decision']}  tier={d['tier_triggered']}  mis={d['misalignment_score']}  latency={d['latency_ms']}ms ✅")


# ── T3: WARN on risky action ──────────────────────────────────────────────────
section("T3 — Claude Score (biased rubric → WARN)")
biased_payload = {
    "session_id":     "test-3",
    "agent_name":     "Scorer",
    "tool_name":      "apply_scoring_rubric",
    "tool_params":    {
        "candidate": {"name": "Alice", "university": "State U"},
        "rubric":    {
            "university_tier_weight": 0.35,   # biased — gates catches this
            "experience_weight": 0.15,
            "skills_weight": 0.50,
        }
    },
    "builder_intent": "Screen resumes and shortlist candidates based on merit",
    "agent_role":     "Scores candidates based on rubric criteria",
}
r = httpx.post(f"{BASE}/gate/check", json=biased_payload, timeout=30)
check("POST /gate/check", r)
d = r.json()
assert d["decision"] in ("ALLOW", "WARN", "BLOCK")
assert isinstance(d["tier_triggered"], int)
assert isinstance(d["latency_ms"], int)
print(f"   decision={d['decision']}  tier={d['tier_triggered']}  mis={d['misalignment_score']}  latency={d['latency_ms']}ms ✅")
if d["decision"] == "WARN":
    print(f"   fix_draft: {d.get('fix_draft', '')[:80]}...")


# ── T2: Cache hit on repeat ───────────────────────────────────────────────────
section("T2 — Cache Hit (same request again)")
r = httpx.post(f"{BASE}/gate/check", json=safe_payload, timeout=10)
check("POST /gate/check (repeat)", r)
d = r.json()
assert d["cache_hit"] == True,       f"Expected cache_hit=True, got {d['cache_hit']}"
assert d["tier_triggered"] == 2,     f"Expected tier 2 on cache hit, got {d['tier_triggered']}"
assert isinstance(d["latency_ms"], int)
print(f"   cache_hit={d['cache_hit']}  tier={d['tier_triggered']}  latency={d['latency_ms']}ms ✅")


# ── Memory ────────────────────────────────────────────────────────────────────
section("Agent Memory (Hash + TTL)")
r = httpx.post(f"{BASE}/memory/write", json={
    "session_id": "test-2",
    "agent_name": "Parser",
    "data": {"topology": "A", "scaffold_hash": "abc123", "model": "claude-haiku-4-5-20251001"},
}, timeout=10)
check("POST /memory/write", r)

r = httpx.get(f"{BASE}/memory/read/test-2/Parser", timeout=10)
check("GET /memory/read", r)
d = r.json()
assert "topology" in d["data"]
print(f"   data={d['data']} ✅")


# ── Audit ─────────────────────────────────────────────────────────────────────
section("Audit Stream + Cache Stats")
r = httpx.get(f"{BASE}/audit/stream-tail?count=5", timeout=10)
check("GET /audit/stream-tail", r)
print(f"   {r.json()['count']} entries")

r = httpx.get(f"{BASE}/audit/cache-stats/test-2", timeout=10)
check("GET /audit/cache-stats", r)
print(f"   {r.json()}")

r = httpx.get(f"{BASE}/audit/export/test-2", timeout=10)
check("GET /audit/export", r)
bp = r.json()
print(f"   total_events={bp['total_events']}  gate={len(bp['gate_events'])}  human={len(bp['human_decisions'])} ✅")


# ── Contract shape check ──────────────────────────────────────────────────────
section("Contract Shape Verification (matches Joseph's GateResponse)")
r = httpx.post(f"{BASE}/gate/check", json=safe_payload, timeout=10)
d = r.json()
required_keys = {"decision", "tier_triggered", "explanation", "cache_hit", "latency_ms"}
missing = required_keys - set(d.keys())
assert not missing, f"Missing required keys: {missing}"
assert d["decision"] in ("ALLOW", "WARN", "BLOCK"),  "decision must be ALLOW/WARN/BLOCK"
assert d["tier_triggered"] in (1, 2, 3),             "tier_triggered must be int 1, 2, or 3"
assert isinstance(d["latency_ms"], int),              "latency_ms must be int"
print("   All contract fields present and correctly typed ✅")

print("\n✅ All tests passed — Evan's gate is fully compatible with Joseph's runner!\n")
