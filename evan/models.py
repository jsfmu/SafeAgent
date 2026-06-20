"""
Interface contracts — matched exactly to Joseph's models.py GateRequest/GateResponse.
Source of truth: SafeAgent-main/backend/models.py
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


# ── GATE INPUT  (Joseph → Evan) — matches GateRequest in Joseph's models.py ──

class GateInput(BaseModel):
    session_id:     str
    agent_name:     str
    tool_name:      str
    tool_params:    dict
    builder_intent: str
    agent_role:     str


# ── GATE OUTPUT  (Evan → Joseph) — matches GateResponse in Joseph's models.py ─
#
# decision:       "ALLOW" | "WARN" | "BLOCK"   (uppercase, Joseph's Literal)
# tier_triggered: 1 | 2 | 3                    (int, not "T1"/"T2"/"T3")
# latency_ms:     int                           (not float)

class GateOutput(BaseModel):
    decision:           Literal["ALLOW", "WARN", "BLOCK"]
    tier_triggered:     Literal[1, 2, 3]
    misalignment_score: Optional[int] = None
    oversight_score:    Optional[int] = None
    explanation:        str
    fix_draft:          Optional[str] = None
    cache_hit:          bool
    latency_ms:         int           # int to match Joseph's model


# ── HUMAN OVERRIDE  (Utkarsh UI → Evan, mirroring HITLDecision shape) ─────────

class HumanOverride(BaseModel):
    session_id:      str
    agent_name:      str
    tool_name:       str
    decision:        Literal["approve_fix", "modify", "override"]
    modified_params: Optional[dict] = None


# ── PUB/SUB EVENT  (Evan → Utkarsh frontend SSE) ─────────────────────────────

class PubSubEvent(BaseModel):
    event_type:  str
    agent_name:  str
    status:      str
    timestamp:   float
    score:       Optional[int] = None
