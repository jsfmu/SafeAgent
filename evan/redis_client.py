"""
Redis client — async connection pool for Redis Cloud (TLS).
Redis Cloud URLs look like:
  rediss://:PASSWORD@redis-XXXXX.c1.us-east-1-2.ec2.cloud.redislabs.com:PORT
The 'rediss://' scheme (double-s) enables TLS automatically.
"""

import os
import ssl
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL env var is not set — check your .env file")

    # Redis Cloud requires TLS. redis.asyncio handles rediss:// automatically,
    # but we pass ssl_cert_reqs=NONE to avoid hostname verification issues on Cloud.
    if url.startswith("rediss://"):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            ssl_cert_reqs=None,
        )
    else:
        _redis = aioredis.from_url(url, decode_responses=True)

    await _redis.ping()
    # Mask password in log
    safe_url = url.split("@")[-1] if "@" in url else url
    print(f"[Redis] Connected to {safe_url}")


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised — call init_redis() first")
    return _redis
