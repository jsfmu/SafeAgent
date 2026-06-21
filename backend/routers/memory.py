"""
Agent Memory Router
Stores per-session, per-agent memory as JSON strings in Redis with TTL.
Using SET/GET instead of HSET to maximise Redis Cloud compatibility.
"""

import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from redis_client import get_redis

router = APIRouter()

MEM_PREFIX = "safeagent:mem:"
DEFAULT_TTL = 86400  # 24 hours


class MemoryWrite(BaseModel):
    session_id:  str
    agent_name:  str
    data:        dict           # arbitrary key-value pairs
    ttl_seconds: Optional[int] = DEFAULT_TTL


@router.post("/write")
async def write_memory(req: MemoryWrite):
    """Store or update agent memory. Merges with existing data. Resets TTL on every write."""
    try:
        r   = get_redis()
        key = f"{MEM_PREFIX}{req.session_id}:{req.agent_name}"

        existing_raw = await r.get(key)
        existing: dict = json.loads(existing_raw) if existing_raw else {}

        str_data = {k: str(v) for k, v in req.data.items()}
        merged = {**existing, **str_data, "_updated_at": str(time.time())}

        ttl = req.ttl_seconds or DEFAULT_TTL
        await r.set(key, json.dumps(merged), ex=ttl)
        return {"status": "ok", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Memory write failed: {e}")


@router.get("/read/{session_id}/{agent_name}")
async def read_memory(session_id: str, agent_name: str):
    """Retrieve all memory fields for a session+agent."""
    try:
        r   = get_redis()
        key = f"{MEM_PREFIX}{session_id}:{agent_name}"
        raw = await r.get(key)
        if not raw:
            raise HTTPException(status_code=404, detail="No memory found for this agent/session")
        data = json.loads(raw)
        ttl  = await r.ttl(key)
        return {"session_id": session_id, "agent_name": agent_name, "data": data, "ttl_seconds": ttl}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Memory read failed: {e}")


@router.delete("/clear/{session_id}/{agent_name}")
async def clear_memory(session_id: str, agent_name: str):
    """Remove all memory for a session+agent (e.g. after session ends)."""
    try:
        r       = get_redis()
        key     = f"{MEM_PREFIX}{session_id}:{agent_name}"
        deleted = await r.delete(key)
        return {"status": "deleted" if deleted else "not_found", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Memory clear failed: {e}")
