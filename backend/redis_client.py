"""
Redis client -- async connection pool for Redis Cloud.
Uses short socket_timeout so callers (which wrap in try/except) fail quickly.
"""

from __future__ import annotations
import asyncio
import os
import ssl
from pathlib import Path
from typing import Optional
import redis.asyncio as aioredis
from dotenv import load_dotenv

_HERE = Path(__file__).parent
load_dotenv(dotenv_path=_HERE / ".env", override=False)

_redis: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    global _redis
    load_dotenv(dotenv_path=_HERE / ".env", override=False)
    url = os.getenv("REDIS_URL")
    if not url or "YOUR_" in url:
        print("[Redis] REDIS_URL not configured -- Redis features disabled", flush=True)
        return

    kwargs = dict(
        decode_responses=True,
        max_connections=20,
        socket_timeout=3,            # fail fast -- callers wrap in try/except
        socket_connect_timeout=15,   # allow more time for initial TCP connection
        socket_keepalive=True,
        retry_on_timeout=False,
        health_check_interval=30,
    )
    if url.startswith("rediss://"):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        pool = aioredis.from_url(url, ssl_cert_reqs=None, **kwargs)
    else:
        pool = aioredis.from_url(url, **kwargs)

    # Retry ping up to 3 times in case of transient startup latency
    for attempt in range(1, 4):
        try:
            await pool.ping()
            _redis = pool
            safe_url = url.split("@")[-1] if "@" in url else url
            print(f"[Redis] Connected to {safe_url}", flush=True)
            return
        except Exception as e:
            if attempt < 3:
                print(f"[Redis] Ping attempt {attempt} failed ({e}), retrying...", flush=True)
                await asyncio.sleep(2)
            else:
                print(f"[Redis] Connection failed after 3 attempts ({e}) -- Redis features disabled", flush=True)
                _redis = None


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_redis() -> aioredis.Redis:
    if _redis is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Redis not connected -- set REDIS_URL in backend/.env")
    return _redis
