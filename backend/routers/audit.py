"""
Audit Export Router
Reads the Redis Stream of gate events and exports them as safe-agent-blueprint.json.
Utkarsh's UI downloads this via the "Download blueprint" button.
"""

import json
import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis_client import get_redis

router = APIRouter()

STREAM_KEY = "safeagent:gate:stream"


def _fields_to_dict(fields) -> dict:
    """Upstash xrange returns fields as a flat list [k, v, k, v, ...]; redis-py returns a dict."""
    if isinstance(fields, dict):
        return fields
    it = iter(fields)
    return {k: v for k, v in zip(it, it)}


@router.get("/export/{session_id}")
async def export_blueprint(session_id: str):
    """
    Read all stream entries for a session and return safe-agent-blueprint.json.
    Every gate event + human decision is included.
    """
    r = get_redis()

    # Read up to 1000 entries from the stream
    raw_entries = await r.xrange(STREAM_KEY, count=1000)

    # Filter to this session
    events = []
    for entry_id, raw_fields in raw_entries:
        fields = _fields_to_dict(raw_fields)
        if fields.get("session_id") == session_id:
            events.append({
                "stream_id": entry_id,
                **fields,
            })

    blueprint = {
        "schema_version": "1.0",
        "session_id":      session_id,
        "exported_at":     time.time(),
        "total_events":    len(events),
        "gate_events":     [e for e in events if e.get("event_type") != "human_override"],
        "human_decisions": [e for e in events if e.get("event_type") == "human_override"],
    }

    return JSONResponse(
        content=blueprint,
        headers={"Content-Disposition": "attachment; filename=safe-agent-blueprint.json"},
    )


@router.get("/stream-tail")
async def stream_tail(count: int = 50):
    """
    Return the last N entries from the gate stream (for the Arize/debug panel).
    """
    r   = get_redis()
    raw = await r.xrevrange(STREAM_KEY, count=count)
    entries = [{"stream_id": eid, **_fields_to_dict(fields)} for eid, fields in raw]
    return {"entries": entries, "count": len(entries)}


@router.get("/cache-stats/{session_id}")
async def cache_stats(session_id: str):
    """
    Cache hit stats for the Proof Panel (Prediction vs Reality view).
    """
    r   = get_redis()
    raw = await r.xrange(STREAM_KEY, count=1000)

    hits   = 0
    misses = 0
    total_latency = 0.0
    decisions = {"allow": 0, "flag": 0, "block": 0}

    for _, raw_fields in raw:
        fields = _fields_to_dict(raw_fields)
        if fields.get("session_id") != session_id:
            continue
        if fields.get("cache_hit") == "True":
            hits += 1
        else:
            misses += 1
        total_latency += float(fields.get("latency_ms", 0))
        d = fields.get("decision", "")
        if d in decisions:
            decisions[d] += 1

    total = hits + misses
    return {
        "session_id":       session_id,
        "cache_hits":       hits,
        "cache_misses":     misses,
        "hit_rate_pct":     round(hits / total * 100, 1) if total else 0,
        "avg_latency_ms":   round(total_latency / total, 1) if total else 0,
        "decisions":        decisions,
    }
