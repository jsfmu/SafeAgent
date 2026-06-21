"""
Claude-backed executor for arbitrary scaffolded tools.

When a tool name isn't in TOOL_FNS (i.e. it's a custom tool invented by the
scaffolder for the user's domain), this calls the agent's designated Claude model
to generate a realistic result — using the agent's own system_prompt as context.

This makes every scaffolded workflow functional for any user prompt.
AnthropicInstrumentor auto-spans these calls so Arize gets real token/cost data.
"""
from __future__ import annotations
import json
from models import AgentDefinition
from claude_client import call_structured

_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "description": "One of: success | partial | error",
        },
        "result": {
            "type": "object",
            "description": "The structured output this tool would realistically return.",
        },
        "summary": {
            "type": "string",
            "description": "One sentence describing what was done and the key finding.",
        },
    },
    "required": ["status", "result", "summary"],
}


def execute_with_claude(
    agent: AgentDefinition,
    tool_name: str,
    tool_params: dict,
    builder_intent: str,
    prior_state_context: dict | None = None,
) -> dict:
    """
    Synchronous — call via asyncio.run_in_executor so it doesn't block the event loop.

    Uses the agent's own model tier (Haiku for simple agents, Sonnet for reasoning)
    and the agent's system_prompt from the scaffold as the execution context.
    """
    state_snippet = ""
    if prior_state_context:
        relevant = {
            k: v for k, v in prior_state_context.items()
            if k not in ("input_data", "raw_input")
            and not k.startswith("_")
            and isinstance(v, (str, int, float, bool, dict, list))
        }
        if relevant:
            state_snippet = (
                "\n\nContext from prior steps in this workflow:\n"
                + json.dumps(relevant, indent=2, default=str)[:2000]
            )

    user_msg = (
        f"You are executing tool `{tool_name}` as the {agent.role}.\n\n"
        f"Workflow goal: {builder_intent}\n\n"
        f"Tool parameters:\n{json.dumps(tool_params, indent=2, default=str)}"
        f"{state_snippet}\n\n"
        "Return a realistic, domain-specific result that this tool would produce "
        "in a real implementation. Be concrete — include actual values, not placeholders."
    )

    return call_structured(
        model=agent.model,
        system=agent.system_prompt,
        messages=[{"role": "user", "content": user_msg}],
        tool_schema=_RESULT_SCHEMA,
        tool_name="tool_result",
        cache_system=True,
    )
