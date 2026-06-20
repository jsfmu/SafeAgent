# Deployment Guide — SafeAgent

## Stack
| Service | Platform | URL pattern |
|---------|----------|-------------|
| Frontend (React/Vite) | **Vercel** | `safeagent.vercel.app` |
| Backend (FastAPI + LangGraph) | **Railway** | `safeagent-backend.up.railway.app` |
| Redis | **Railway** (Redis plugin) or **Redis Cloud** free tier | internal Railway URL |
| Arize Phoenix | Local only for hackathon (or Arize Cloud) | `localhost:6006` |

---

## Frontend → Vercel

### One-time setup
```bash
npm i -g vercel
cd frontend
vercel        # follow prompts, link to project
```

### Set env vars in Vercel dashboard
```
VITE_API_URL   = https://safeagent-backend.up.railway.app
VITE_USE_MOCK  = false
```

### Deploy
```bash
cd frontend && vercel --prod
```

---

## Backend → Railway

### One-time setup
1. Go to railway.app → New Project → Deploy from GitHub
2. Select the repo, set root directory to `backend/`
3. Add Redis plugin: `+ New` → `Database` → `Redis`
4. Copy `REDIS_URL` from Redis plugin → paste into backend service env vars

### Required env vars on Railway
```
ANTHROPIC_API_KEY   = sk-ant-...
REDIS_URL           = redis://... (from Railway Redis plugin)
ARIZE_API_KEY       = (optional, only for cloud Phoenix)
FRONTEND_ORIGIN     = https://safeagent.vercel.app
```

### railway.toml (put this in backend/ when Joseph creates it)
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
```

### CORS — Joseph must add to FastAPI
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Integration checklist (after teammates push)

```bash
# 1. Pull latest
git pull origin main

# 2. Install backend deps
cd backend && pip install -r requirements.txt

# 3. Set local .env
cp backend/.env.example backend/.env
# fill in ANTHROPIC_API_KEY, REDIS_URL

# 4. Start Redis locally (if not using Railway)
docker run -p 6379:6379 redis:alpine

# 5. Start backend
cd backend && uvicorn main:app --reload --port 8000

# 6. Start Arize Phoenix (optional for local proof panel)
python -m phoenix.server.main serve  # http://localhost:6006

# 7. Start frontend (real backend mode)
cd frontend
echo "VITE_API_URL=http://localhost:8000" > .env.local
echo "VITE_USE_MOCK=false" >> .env.local
npm run dev
```

---

## SSE / Redis Pub/Sub on Railway

Railway supports long-lived connections. Make sure:
- `keep_alive` timeout set to > 60s (Railway default is fine)
- The SSE endpoint at `/events/{session_id}` uses `StreamingResponse` (already in `arize/sse.py`)
- Redis Pub/Sub channel name: `safe-agent:{session_id}` (agreed interface)

---

## Quick smoke test after deploy
```bash
BACKEND=https://safeagent-backend.up.railway.app

# health
curl $BACKEND/health

# classify
curl -X POST $BACKEND/classify \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hiring agent — screen resumes, score candidates. Merit-based."}'
```
