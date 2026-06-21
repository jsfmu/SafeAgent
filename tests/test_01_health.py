"""Suite 1 — Health & connectivity."""
import pytest


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "version" in body


def test_health_latency_under_500ms(client):
    import time
    t0 = time.perf_counter()
    client.get("/health")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"Health check too slow: {elapsed_ms:.0f}ms"
