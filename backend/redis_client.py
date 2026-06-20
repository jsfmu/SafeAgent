"""
Redis client — async connection pool for Redis Cloud (TLS).
Redis Cloud URLs look like:
  rediss://:PASSWORD@redis-XXXXX.c1.us-east-1-2.ec2.cloud.redislabs.com:PORT
The 'rediss://' scheme (double-s) enables TLS automatically.
"""

from __future__ import annotations
import os
import ssl
from typing import Optional
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

_redis: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    global _redis
    url = os.getenv("REDIS_URL")
    if not url or "YOUR_" in url:
        print("[Redis] REDIS_URL not configured — Redis features disabled (gate, pubsub, audit, memory)")
        return

    try:
        if url.startswith("rediss://"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            _redis = aioredis.from_url(url, decode_responses=True, ssl_cert_reqs=None)
        else:
            _redis = aioredis.from_url(url, decode_responses=True)

        await _redis.ping()
        safe_url = url.split("@")[-1] if "@" in url else url
        print(f"[Redis] Connected to {safe_url}")
    except Exception as e:
        print(f"[Redis] Connection failed ({e}) — Redis features disabled")


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_redis() -> aioredis.Redis:
    if _redis is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Redis not connected — set REDIS_URL in backend/.env")
    return _redis
