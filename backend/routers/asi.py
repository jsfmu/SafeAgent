"""
ASI:One / AgentVerse discovery router.

POST /asi/discover  — query AgentVerse for existing agents matching the domain.
                      Falls back to mock data if AGENTVERSE_API_KEY is not set.
"""
from __future__ import annotations
import os
from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

AGENTVERSE_SEARCH_URL = "https://agentverse.ai/v1/search"
_API_KEY: Optional[str] = None


def _get_key() -> Optional[str]:
    global _API_KEY
    if _API_KEY is None:
        _API_KEY = os.getenv("AGENTVERSE_API_KEY")
    return _API_KEY


class DiscoverRequest(BaseModel):
    domain: str
    description: str
    limit: int = 5


class AgentverseAgent(BaseModel):
    address: str
    name: str
    status: str
    total_interactions: int
    recent_interactions: int
    rating: Optional[float] = None
    category: str
    last_updated: str


class DiscoverResponse(BaseModel):
    agents: list[AgentverseAgent]
    source: str   # "agentverse" | "mock"
    query: str


@router.post("/discover", response_model=DiscoverResponse)
async def discover_agents(req: DiscoverRequest):
    key = _get_key()
    query = f"{req.domain} {req.description}"

    if key and "YOUR_" not in key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.post(
                    AGENTVERSE_SEARCH_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "search_text": query,
                        "sort": "relevancy",
                        "direction": "desc",
                        "cutoff": "balanced",
                        "limit": req.limit,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    agents = data if isinstance(data, list) else data.get("agents", [])
                    return DiscoverResponse(
                        agents=[AgentverseAgent(**a) for a in agents[:req.limit]],
                        source="agentverse",
                        query=query,
                    )
        except Exception:
            pass  # fall through to mock

    return _mock_response(req.domain, query)


def _mock_response(domain: str, query: str) -> DiscoverResponse:
    domain_lower = domain.lower()

    if "hiring" in domain_lower or "recruit" in domain_lower or "hr" in domain_lower:
        agents = [
            AgentverseAgent(address="agent1qv8r2x9p3k", name="HireBot Pro", status="active",
                            total_interactions=3240, recent_interactions=128, rating=4.7,
                            category="community", last_updated="2026-06-10T12:00:00Z"),
            AgentverseAgent(address="agent1qt7m5n2c1w", name="Resume Ranker", status="active",
                            total_interactions=1870, recent_interactions=54, rating=4.4,
                            category="community", last_updated="2026-06-08T09:00:00Z"),
        ]
    elif "customer" in domain_lower or "support" in domain_lower:
        agents = [
            AgentverseAgent(address="agent1qz3k9p2r7s", name="SupportGenie", status="active",
                            total_interactions=8120, recent_interactions=340, rating=4.9,
                            category="fetch-ai", last_updated="2026-06-15T08:00:00Z"),
            AgentverseAgent(address="agent1qa5t1b8m4n", name="TicketBot", status="active",
                            total_interactions=2650, recent_interactions=89, rating=4.5,
                            category="community", last_updated="2026-06-12T14:00:00Z"),
        ]
    elif "research" in domain_lower or "search" in domain_lower:
        agents = [
            AgentverseAgent(address="agent1qr4w2v6k9x", name="DeepResearch Agent", status="active",
                            total_interactions=5430, recent_interactions=210, rating=4.8,
                            category="fetch-ai", last_updated="2026-06-14T11:00:00Z"),
        ]
    else:
        agents = [
            AgentverseAgent(address="agent1qg7h3n5p1y", name="General Automation Agent", status="active",
                            total_interactions=990, recent_interactions=32, rating=4.2,
                            category="community", last_updated="2026-06-05T16:00:00Z"),
        ]

    return DiscoverResponse(agents=agents, source="mock", query=query)
