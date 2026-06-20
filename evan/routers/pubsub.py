"""
Pub/Sub Router
Evan auto-publishes on every gate event.
Utkarsh's Vercel frontend subscribes via SSE from the browser (client-side fetch).

SSE works perfectly from a browser → Railway-hosted FastAPI.
Do NOT call SSE from a Vercel serverless function — connect from the browser directly.
"""

import json
import time
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from redis_client import get_redis
from models import PubSubEvent

router = APIRouter()

PUBSUB_CHANNEL = "safeagent:events"


@router.post("/publish")
async def publish_event(event: PubSubEvent):
    """
    Joseph calls this to broadcast LangGraph node status (running/done/blocked).
    Gate auto-calls this too — so Utkarsh only needs to subscribe, not publish.
    """
    r = get_redis()
    payload = event.model_dump()
    payload["timestamp"] = time.time()
    await r.publish(PUBSUB_CHANNEL, json.dumps(payload))
    return {"status": "published", "channel": PUBSUB_CHANNEL}


@router.get("/subscribe")
async def subscribe_sse(request: Request):
    """
    Server-Sent Events — Utkarsh's browser connects here directly.

    Frontend usage (plain JS, works in any Next.js component):
        const es = new EventSource('https://YOUR-RAILWAY-URL/pubsub/subscribe');
        es.onmessage = (e) => {
            const event = JSON.parse(e.data);
            // { event_type, agent_name, status, score, timestamp }
        };
        es.onerror = () => es.close();
    """
    async def event_stream():
        r = get_redis()
        # Each SSE connection needs its own pubsub object
        ps = r.pubsub()
        await ps.subscribe(PUBSUB_CHANNEL)
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                msg = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    yield f"data: {msg['data']}\n\n"
                else:
                    # Keepalive every second — prevents Vercel/proxies from
                    # closing the connection after 30s idle
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        finally:
            await ps.unsubscribe(PUBSUB_CHANNEL)
            await ps.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",   # disables Nginx buffering on Railway
            "Access-Control-Allow-Origin": "*",    # SSE needs its own CORS header
        },
    )
