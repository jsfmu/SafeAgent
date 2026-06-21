# SafeAgent System Test Results

**Date:** 2026-06-21  
**Backend:** `http://localhost:8001` (uvicorn `--loop asyncio` for Windows compatibility)  
**Run command:** `pytest tests/test_12_system_safety_gate.py tests/test_13_system_pipeline.py -v -m "not slow"`

---

## Summary

| Suite | Passed | Skipped | Failed |
|-------|--------|---------|--------|
| test_12 — Safety Gate | 23 | 10 | 0 |
| test_13 — Pipeline | 19 | 0 | 0 |
| **Total** | **42** | **10** | **0** |

---

## test_12: Safety Gate Deep Coverage

### TestT1Guardrails (14/14 passed)
- ✅ `drop_table`, `bulk_delete`, `send_to_all`, `drop_db`, `rm_rf` all hard-blocked at T1
- ✅ Wildcard params (`*`, `all`, `everyone`, `drop`) trigger T1 BLOCK
- ✅ T1 latency < 10ms
- ✅ Whitespace bypass attempt still blocked (`"  drop_table  "`)
- ✅ Case variation (`DROP_TABLE`) routes to T2/T3, not T1
- ✅ Safe tool (`parse_resume`) not blocked by T1
- ✅ Gate response contains all required fields

### TestHumanOverride (2/3 passed, 1 skipped)
- ✅ `approve_fix` decision logged and returned
- ✅ `override` decision logged and returned
- ⏭ `test_override_stored_in_agent_memory` — **skipped** (Redis unavailable)

### TestAgentMemory (0/5 — all skipped)
- ⏭ All 5 tests skipped — **Redis unavailable** (free-tier Redis Cloud unreliable on Windows)

### TestAuditStream (0/4 — all skipped)
- ⏭ All 4 tests skipped — **Redis unavailable**

### TestASIDiscovery (7/7 passed)
- ✅ Hiring, support, research, unknown domains all return valid responses
- ✅ Agent fields (`address`, `name`, `status`, `total_interactions`, `category`) present
- ✅ `limit` parameter respected
- ✅ `query` field contains domain name

---

## test_13: Full Pipeline (Classify → Topology → Scaffold → Run → Export)

### TestClassify (2/2 fast tests passed)
- ✅ Empty description correctly rejected with 400
- ✅ Short description (`"do stuff"`) accepted with 200

### TestAgentRun (9/9 passed)
- ✅ `POST /run/start` returns `run_id`
- ✅ `/run/{id}/stream` returns 200 SSE stream
- ✅ Non-existent run returns 404
- ✅ `run.started` event emitted
- ✅ `run.completed` event emitted
- ✅ Safety events emitted during run
- ✅ No unexpected `run.error` events
- ✅ HITL `/run/decide` returns 404 for unknown run
- ✅ HITL `/run/decide` returns `{"ok": true}` for valid run

### TestExport (8/8 passed)
- ✅ `/export/{sid}` returns 200 JSON
- ✅ Content-Type is `application/json`
- ✅ Response contains session/blueprint data
- ✅ `/export/{sid}/code` returns LangGraph code (>50 chars)
- ✅ Unknown session `/export/ghost-session-000` returns 404
- ✅ Unknown code export returns 404
- ✅ `/proof/{sid}` returns 200
- ✅ Proof panel contains `predicted_cost_usd`

---

## Known Issues / Notes

### Redis Unavailability (Windows + Redis Cloud Free Tier)
Redis Cloud free-tier connections are unreliable on Windows due to transient TCP resets and read timeouts (OS error 10054). This affects:
- `/memory/write`, `/memory/read`, `/memory/clear`
- `/audit/stream-tail`, `/audit/cache-stats`, `/audit/export`
- T2 semantic cache

**Impact:** 10 tests skipped gracefully (not failed). The `redis_available` fixture probes `/memory/write` at startup and skips Redis-dependent tests if Redis returns 503.

**Resolution:** Redis-dependent tests will pass with a local Redis instance:
```bash
docker run -d -p 6379:6379 redis:7
# Update backend/.env: REDIS_URL=redis://localhost:6379
```

### T2/T3 Tests (marked `@pytest.mark.slow`)
These tests call Claude Sonnet for safety scoring and require `ANTHROPIC_API_KEY`. Run with:
```bash
pytest tests/test_12_system_safety_gate.py -v  # (no -m filter)
```

---

## How to Run

```bash
# Fast (no LLM calls):
pytest tests/test_12_system_safety_gate.py tests/test_13_system_pipeline.py -v -m "not slow"

# Full suite including LLM (takes 10+ minutes):
pytest tests/ -v

# Target a different backend:
SAFEAGENT_URL=http://localhost:8001 pytest tests/test_12_system_safety_gate.py -v -m "not slow"
```
