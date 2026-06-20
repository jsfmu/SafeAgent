"""
Agent Memory Router
Stores per-session, per-agent memory as Redis Hashes with TTL.
Joseph writes scaffolding context; Evan reads it at gate-check time.
"""

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


class MemoryRead(BaseModel):
    session_id: str
    agent_name: str


@router.post("/write")
async def write_memory(req: MemoryWrite):
    """Store or update agent memory fields (Hash). Resets TTL on every write."""
    r   = get_redis()
    key = f"{MEM_PREFIX}{req.session_id}:{req.agent_name}"

    # Stringify all values — Redis Hash values must be strings
    str_data = {k: str(v) for k, v in req.data.items()}
    str_data["_updated_at"] = str(time.time())

    await r.hset(key, mapping=str_data)
    await r.expire(key, req.ttl_seconds or DEFAULT_TTL)
    return {"status": "ok", "key": key}


@router.get("/read/{session_id}/{agent_name}")
async def read_memory(session_id: str, agent_name: str):
    """Retrieve all memory fields for a session+agent."""
    r   = get_redis()
    key = f"{MEM_PREFIX}{session_id}:{agent_name}"
    data = await r.hgetall(key)
    if not data:
        raise HTTPException(status_code=404, detail="No memory found for this agent/session")
    ttl = await r.ttl(key)
    return {"session_id": session_id, "agent_name": agent_name, "data": data, "ttl_seconds": ttl}


@router.delete("/clear/{session_id}/{agent_name}")
async def clear_memory(session_id: str, agent_name: str):
    """Remove all memory for a session+agent (e.g. after session ends)."""
    r   = get_redis()
    key = f"{MEM_PREFIX}{session_id}:{agent_name}"
    deleted = await r.delete(key)
    return {"status": "deleted" if deleted else "not_found", "key": key}
