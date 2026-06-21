"""
Deepgram voice router — TTS + keyword safety check.

Routes:
  POST /voice/tts      → stream audio from Deepgram TTS
  POST /voice/keywords → check description text for dangerous phrases
"""
from __future__ import annotations
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"

# Dangerous phrases caught BEFORE Claude ever classifies the description
DANGEROUS_PHRASES = [
    "delete all", "delete everything", "drop table", "drop database",
    "drop_table", "drop_db", "send to all", "send to everyone",
    "send to all users", "without review", "without approval",
    "skip verification", "override safety", "bypass auth",
    "bulk delete", "rm -rf", "ignore permissions", "admin override",
    "override all", "force delete",
]


class TTSRequest(BaseModel):
    text: str
    model: str = "aura-asteria-en"  # Deepgram's natural-sounding TTS model


class KeywordCheckRequest(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """
    Convert text to speech via Deepgram TTS.
    Streams audio/mpeg back — frontend plays it directly.
    Used for: safety warning readout when gate flags an action.
    """
    if not DEEPGRAM_API_KEY:
        raise HTTPException(503, "DEEPGRAM_API_KEY not configured in backend .env")

    async def stream_audio():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{DEEPGRAM_TTS_URL}?model={req.model}",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"text": req.text},
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise HTTPException(resp.status_code, f"Deepgram TTS error: {body.decode()}")
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield chunk

    return StreamingResponse(
        stream_audio(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/keywords")
async def check_keywords(req: KeywordCheckRequest):
    """
    Scan description text for dangerous phrases BEFORE scaffolding.
    Called client-side as the user types / after STT transcription.
    Returns flagged phrases so the UI can warn the builder immediately.
    """
    text_lower = req.text.lower()
    flagged = [p for p in DANGEROUS_PHRASES if p in text_lower]
    return {
        "flagged": flagged,
        "safe": len(flagged) == 0,
        "warning": (
            f"Dangerous phrase detected: '{flagged[0]}' — "
            "this may be blocked by the safety gate before execution."
        ) if flagged else None,
    }
