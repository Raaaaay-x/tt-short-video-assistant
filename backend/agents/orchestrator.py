"""Orchestrator Agent — coordinates the multi-agent TikTok content pipeline."""

import json, uuid
from typing import AsyncIterator

from .context import AgentContext
from . import deconstructor, script_writer, guardrail


async def run_pipeline(
    transcript: str,
    source_url: str = "",
    provider: str = "deepseek",
    api_key: str = "",
    persona: dict | None = None,
) -> AsyncIterator[dict]:
    """Run the full multi-agent pipeline. Yields SSE events for streaming to frontend."""

    session_id = uuid.uuid4().hex[:8]
    ctx = AgentContext()
    ctx.mark_start(session_id)
    ctx.transcript = transcript
    ctx.source_url = source_url
    if persona:
        ctx.persona = persona

    yield {"type": "start", "session_id": session_id, "message": "Starting multi-agent pipeline"}

    # Agent 1: Deconstruct
    yield {"type": "agent_start", "agent": "deconstructor", "message": "Deconstruct Agent: analyzing viral structure..."}
    try:
        decon_text = await deconstructor.run(ctx, provider=provider, api_key=api_key)
        yield {"type": "agent_done", "agent": "deconstructor", "message": "Deconstruction complete", "output": decon_text}
    except Exception as e:
        yield {"type": "agent_error", "agent": "deconstructor", "error": str(e)}
        return

    # Agent 2: Script Writer
    yield {"type": "agent_start", "agent": "script_writer", "message": "Script Agent: adapting for target brand..."}
    try:
        script_text = await script_writer.run(ctx, provider=provider, api_key=api_key)
        yield {"type": "agent_done", "agent": "script_writer", "message": "Script generated", "output": script_text}
    except Exception as e:
        yield {"type": "agent_error", "agent": "script_writer", "error": str(e)}
        return

    # Agent 3: Guardrail
    yield {"type": "agent_start", "agent": "guardrail", "message": "Guardrail Agent: checking TikTok policy + FTC compliance..."}
    issues = await guardrail.run(ctx)
    yield {
        "type": "agent_done",
        "agent": "guardrail",
        "message": "All clear" if not issues else f"{len(issues)} issue(s) found",
        "output": guardrail.format_report(issues),
        "issues": issues,
    }

    # Done
    ctx.mark_done()
    yield {
        "type": "done",
        "session_id": session_id,
        "message": "Pipeline complete",
        "summary": ctx.summary(),
        "results": {
            "deconstruction": ctx.deconstruction.get("raw", ""),
            "script": ctx.script,
            "filming_guide": ctx.filming_guide,
            "guardrail_issues": ctx.guardrail_issues,
            "session_id": session_id,
        },
    }
