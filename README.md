# SafeAgent

**Evidence-Backed Agent Builder** — UC Berkeley AI Hackathon 2026

> Scaffold from plain English → intercept every action pre-execution → prove architecture and cost claims with real telemetry.

## Quick start

### Frontend (Utkarsh)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
# Runs in mock mode by default (VITE_USE_MOCK=true in .env)
# Set VITE_USE_MOCK=false when backend is live
```

### Arize Phoenix (Utkarsh — run before backend)
```bash
python arize/setup.py   # install deps once
python -m phoenix.server.main serve   # http://localhost:6006
```

### Backend (Joseph + Evan)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Repo layout

```
frontend/          # React + React Flow + Recharts (Utkarsh)
  src/
    components/    # InputScreen, TopologyPicker, AgentGraph, FlagModal, ProofPanel, AuditLog
    api/client.ts  # API client + MOCK data
    hooks/         # useRealtimeEvents (SSE from Redis Pub/Sub)
    types/         # Shared TypeScript types

arize/             # Arize Phoenix + OpenInference (Utkarsh)
  instrumentation.py  # SessionTracer, trace_node decorator
  sse.py              # FastAPI SSE router for Evan to plug in
  setup.py            # Install deps

backend/           # FastAPI + LangGraph + Redis (Joseph + Evan)
planning/          # Implementation plan + demo docs
```

## Shared interfaces

All types live in `frontend/src/types/index.ts`. The Python equivalent is in the implementation plan.

### Event types published to Redis Pub/Sub (Evan → Frontend)

```json
{ "type": "agent_status", "agent_id": "scorer", "status": "running" }
{ "type": "safety_flag", "flag": { ...SafetyFlag } }
{ "type": "run_complete" }
{ "type": "run_error", "message": "..." }
```

### API endpoints Joseph needs to implement

| Method | Path | Description |
|--------|------|-------------|
| POST | `/classify` | Haiku pre-classifier |
| POST | `/topology` | Sonnet + Extended Thinking topology options |
| POST | `/scaffold` | Meta-agent scaffolder → ScaffoldResult |
| POST | `/run` | Start LangGraph execution |
| POST | `/hitl` | HITL decision (approve/modify/override) |
| GET  | `/proof/{session_id}` | Arize proof data |
| GET  | `/audit/{session_id}` | Redis Stream audit events |
| GET  | `/events/{session_id}` | SSE stream (use arize/sse.py) |
| GET  | `/export/{session_id}` | Blueprint JSON download |

## Flag modal — critical path

The flag modal (`FlagModal.tsx`) is the judge "wow moment". It renders:
- Misalignment + Oversight score meters
- Plain-English explanation from Claude
- Your intent vs. what the agent tried (side by side)
- Auto-generated safer alternative (editable)
- Approve / Modify / Override buttons

Test it standalone: `VITE_USE_MOCK=true npm run dev`, click any example → Build → Run Agents → wait 3.4s for the mock flag to fire.

## Arize instrumentation (for Joseph)

```python
from arize.instrumentation import setup_tracing, trace_node, session_tracer

# At app startup
setup_tracing()

# On each LangGraph node
@trace_node("Candidate Scorer", "haiku-4-5", topology="A")
def scorer_node(state):
    ...

# In /proof endpoint
@app.get("/proof/{session_id}")
def get_proof(session_id: str):
    return session_tracer.get_proof_data(session_id, predicted_cost_usd=0.09)
```
