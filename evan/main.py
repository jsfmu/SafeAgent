"""
SafeAgent - Evan's Safety Gate Service
Redis Cloud + FastAPI → deployed on Railway, consumed by Vercel frontend
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from routers import gate, pubsub, memory, audit
from redis_client import init_redis, close_redis

# Vercel frontend URLs — Railway injects VERCEL_URL at deploy time,
# or you can hardcode your preview + prod URLs here.
VERCEL_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(
    title="SafeAgent Gate API",
    description="Evan's Safety Gate: Guardrails, Semantic Cache, Claude Scoring, Pub/Sub, Audit",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=VERCEL_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",   # covers all preview deploys
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gate.router,   prefix="/gate",   tags=["Safety Gate"])
app.include_router(pubsub.router, prefix="/pubsub", tags=["Pub/Sub"])
app.include_router(memory.router, prefix="/memory", tags=["Agent Memory"])
app.include_router(audit.router,  prefix="/audit",  tags=["Audit Export"])


@app.get("/health")
async def health():
    from redis_client import get_redis
    r = get_redis()
    await r.ping()
    return {
        "status":   "ok",
        "service":  "safeagent-gate",
        "redis":    "connected",
        "origins":  VERCEL_ORIGINS,
    }
