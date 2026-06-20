# SafeAgent — Evan's Service
**Redis Cloud + FastAPI → Railway**
Integrates with Joseph's LangGraph backend and Utkarsh's Vercel frontend.

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env         # fill in REDIS_URL + ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8001
python test_local.py         # verify everything works before pushing
```

API docs: http://localhost:8001/docs

---

## Deploy to Railway

```bash
npm install -g @railway/cli
railway login && railway init && railway up
```

Add these env vars in Railway dashboard:
```
REDIS_URL=rediss://:PASSWORD@HOST.redislabs.com:PORT
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=http://localhost:3000,https://YOUR-APP.vercel.app
```

Tell Joseph to set `SAFETY_GATE_URL=https://YOUR-RAILWAY-URL/gate/check` in his `.env`.

---

## Gate Contract — matched to Joseph's GateResponse

### Input (Joseph → Evan)
`POST /gate/check`
```json
{
  "session_id":     "string",
  "agent_name":     "Scorer",
  "tool_name":      "apply_scoring_rubric",
  "tool_params":    { "candidate": {}, "rubric": {} },
  "builder_intent": "Screen resumes and email shortlist",
  "agent_role":     "Scores candidates based on rubric"
}
```

### Output (Evan → Joseph)
```json
{
  "decision":           "WARN",
  "tier_triggered":     3,
  "misalignment_score": 72,
  "oversight_score":    80,
  "explanation":        "Rubric weights university tier at 35%, introducing bias.",
  "fix_draft":          "Reweight to emphasise skills and experience instead.",
  "cache_hit":          false,
  "latency_ms":         843
}
```

**decision** values:
- `"ALLOW"` → Joseph executes the tool normally
- `"WARN"`  → Joseph generates auto-fix + waits for HITL (approve_fix / modify / override)
- `"BLOCK"` → T1 hard block only (bulk_delete, send_to_all, etc.) — no recovery

**tier_triggered** values: `1` (T1 guardrails), `2` (cache hit), `3` (Claude scored)

---

## All Endpoints

| Method | Path | Who calls it | What it does |
|--------|------|-------------|--------------|
| POST | `/gate/check` | Joseph (graph_runner) | T1→T2→T3 safety check |
| POST | `/gate/override` | Utkarsh UI | Log human decision to Redis Stream |
| GET  | `/pubsub/subscribe` | Utkarsh browser (SSE) | Real-time event stream |
| POST | `/pubsub/publish` | Joseph | Broadcast agent node status |
| POST | `/memory/write` | Joseph | Store agent context (Hash+TTL) |
| GET  | `/memory/read/{session}/{agent}` | Anyone | Read agent memory |
| GET  | `/audit/export/{session_id}` | Utkarsh UI | Download safe-agent-blueprint.json |
| GET  | `/audit/stream-tail` | Debug | Last N Redis Stream entries |
| GET  | `/audit/cache-stats/{session_id}` | Utkarsh proof panel | Hit rate, avg latency, decisions |
| GET  | `/health` | Railway healthcheck | Redis ping + status |

---

## Redis Cloud URL format
```
rediss://:PASSWORD@HOST.redislabs.com:PORT
```
`rediss://` (double-s) = TLS required for Redis Cloud.

---

## SSE for Utkarsh's Vercel frontend
Connect from the **browser** (not a Vercel serverless function):
```js
const es = new EventSource('https://YOUR-RAILWAY-URL/pubsub/subscribe');
es.onmessage = (e) => {
  const { event_type, agent_name, status, score } = JSON.parse(e.data);
};
```
