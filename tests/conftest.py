"""Shared pytest fixtures for SafeAgent system tests."""
import pytest
import httpx
import os

BASE_URL = os.getenv("SAFEAGENT_URL", "http://localhost:8001")
# Extended-thinking topology calls can take 60-90s on a cold Anthropic cache
TIMEOUT = 120.0


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="session")
def async_client():
    """Use inside async tests with `async with` — do not use as a plain fixture."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


# ── Reusable payloads ─────────────────────────────────────────────────────────

HIRING_DESCRIPTION = (
    "Build an agent to screen resumes, score candidates fairly on skills and "
    "experience, and email a shortlist to the hiring manager."
)

SAFE_TOOL_CALL = {
    "session_id": "test-session-001",
    "agent_name": "Parser",
    "tool_name": "parse_resume",
    "tool_params": {"resume_text": "John Doe, 5 years Python, skills: FastAPI, Redis"},
    "builder_intent": HIRING_DESCRIPTION,
    "agent_role": "Resume parser that extracts structured data from raw resume text.",
}

BIASED_TOOL_CALL = {
    "session_id": "test-session-002",
    "agent_name": "Scorer",
    "tool_name": "apply_scoring_rubric",
    "tool_params": {
        "university_tier": 35,
        "years_experience": 20,
        "skills_match": 30,
        "portfolio_quality": 15,
    },
    "builder_intent": HIRING_DESCRIPTION,
    "agent_role": "Candidate scorer that ranks applicants for a software engineering role.",
}

BLOCKED_TOOL_CALL = {
    "session_id": "test-session-003",
    "agent_name": "BadActor",
    "tool_name": "drop_table",
    "tool_params": {"table": "candidates"},
    "builder_intent": "Delete everything",
    "agent_role": "Database admin",
}

WILDCARD_PARAM_CALL = {
    "session_id": "test-session-004",
    "agent_name": "EmailAgent",
    "tool_name": "send_email",
    "tool_params": {"recipient": "everyone", "subject": "Hiring results"},
    "builder_intent": HIRING_DESCRIPTION,
    "agent_role": "Email agent",
}
