"""
OpenInference instrumentation for SafeAgent LangGraph nodes.
Joseph imports this at the top of his LangGraph module.

Usage:
    from arize.instrumentation import setup_tracing, trace_node, get_proof_data
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# OpenTelemetry + Phoenix setup
# ---------------------------------------------------------------------------

def setup_tracing(project_name: str = "safe-agent") -> None:
    """
    Call once at app startup. Sends traces to Phoenix running on localhost:6006.
    If Phoenix isn't running, traces are silently dropped (no crash).
    """
    try:
        import phoenix as px
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = "http://localhost:6006/v1/traces"
        provider = TracerProvider()
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(provider)

        LangChainInstrumentor().instrument()
        AnthropicInstrumentor().instrument()

        print(f"[Arize] Tracing → Phoenix at {endpoint}")
        print(f"[Arize] View traces: http://localhost:6006  (project: {project_name})")
    except ImportError:
        print("[Arize] Phoenix not installed — traces disabled. Run: python arize/setup.py")
    except Exception as e:
        print(f"[Arize] Tracing init failed: {e} — continuing without traces")


# ---------------------------------------------------------------------------
# Per-session trace accumulator (for proof panel)
# ---------------------------------------------------------------------------

@dataclass
class NodeTrace:
    agent_name: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float
    safety_score: int | None
    topology: str  # "A" or "B"
    step: int


# Cost per 1M tokens (June 2026 pricing)
_COST_PER_M_IN = {"haiku-4-5": 0.80, "sonnet-4-6": 3.00}
_COST_PER_M_OUT = {"haiku-4-5": 4.00, "sonnet-4-6": 15.00}


def compute_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    m = model.replace("claude-", "").replace("-20251001", "")
    cost_in = _COST_PER_M_IN.get(m, 3.00) * tokens_in / 1_000_000
    cost_out = _COST_PER_M_OUT.get(m, 15.00) * tokens_out / 1_000_000
    return round(cost_in + cost_out, 6)


class SessionTracer:
    """
    Accumulates traces per session. Utkarsh's proof panel calls .get_proof_data().
    Joseph calls .record_node() from each LangGraph node.
    """

    def __init__(self):
        self._traces: dict[str, list[NodeTrace]] = defaultdict(list)

    def record_node(
        self,
        session_id: str,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        topology: str = "A",
        safety_score: int | None = None,
    ) -> NodeTrace:
        step = len(self._traces[session_id]) + 1
        t = NodeTrace(
            agent_name=agent_name,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=compute_cost(model, tokens_in, tokens_out),
            safety_score=safety_score,
            topology=topology,
            step=step,
        )
        self._traces[session_id].append(t)
        return t

    def get_proof_data(self, session_id: str, predicted_cost_usd: float) -> dict[str, Any]:
        traces = self._traces.get(session_id, [])
        topo_a = [t for t in traces if t.topology == "A"]
        topo_b = [t for t in traces if t.topology == "B"]

        return {
            "predicted_cost_usd": predicted_cost_usd,
            "topology_a": {
                "actual_cost_usd": round(sum(t.cost_usd for t in topo_a), 6),
                "actual_latency_ms": sum(t.latency_ms for t in topo_a),
                "per_agent": [_trace_to_dict(t) for t in topo_a],
            },
            "topology_b": {
                "actual_cost_usd": round(sum(t.cost_usd for t in topo_b), 6),
                "actual_latency_ms": sum(t.latency_ms for t in topo_b),
                "per_agent": [_trace_to_dict(t) for t in topo_b],
            },
            # Safety drift — populated by /proof endpoint from Redis stats
            "safety_drift": [
                {"run": 1, "misalignment": 0, "oversight": 0},
                {"run": 2, "misalignment": 0, "oversight": 0},
                {"run": 3, "misalignment": 0, "oversight": 0},
            ],
            "redis_cache_hits": 0,
            "redis_total_calls": max(1, len(traces)),
            "tokens_saved": 0,
            "autofix_eval_score": 0.85,      # placeholder until LLM eval is wired
            "hallucination_score": 0.92,      # placeholder
            "prior_flags_on_pattern": 0,
            "ab_winner": "A",
        }


def _trace_to_dict(t: NodeTrace) -> dict:
    return {
        "agent_name": t.agent_name,
        "model": t.model,
        "tokens_in": t.tokens_in,
        "tokens_out": t.tokens_out,
        "latency_ms": t.latency_ms,
        "cost_usd": t.cost_usd,
        "safety_score": t.safety_score,
        "topology": t.topology,
        "step": t.step,
    }


# Singleton used by the FastAPI backend
session_tracer = SessionTracer()


# ---------------------------------------------------------------------------
# LangGraph node decorator
# ---------------------------------------------------------------------------

def trace_node(agent_name: str, model: str, topology: str = "A"):
    """
    Decorator for LangGraph node functions (sync or async).

    Records latency in SessionTracer. Token counts are captured automatically
    by AnthropicInstrumentor (activated in setup_tracing) — do NOT try to
    extract them from the node's dict return value (Bug 4 fix).

    @trace_node("Resume Parser", "haiku-4-5")
    async def _node_parse(self, state):
        ...
    """
    import asyncio as _asyncio
    import functools

    def decorator(fn):
        if _asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                result = await fn(state, *args, **kwargs)
                latency_ms = int((time.perf_counter() - start) * 1000)
                session_id = state.get("session_id", "unknown") if isinstance(state, dict) else "unknown"
                session_tracer.record_node(
                    session_id=session_id,
                    agent_name=agent_name,
                    model=model,
                    tokens_in=0,  # filled by AnthropicInstrumentor auto-spans
                    tokens_out=0,
                    latency_ms=latency_ms,
                    topology=topology,
                )
                return result
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                result = fn(state, *args, **kwargs)
                latency_ms = int((time.perf_counter() - start) * 1000)
                session_id = state.get("session_id", "unknown") if isinstance(state, dict) else "unknown"
                session_tracer.record_node(
                    session_id=session_id,
                    agent_name=agent_name,
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=latency_ms,
                    topology=topology,
                )
                return result
            return sync_wrapper
    return decorator
