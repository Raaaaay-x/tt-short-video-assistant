"""
tt_agent v3.0 — FastAPI Backend with Multi-Agent SSE Streaming

Run: uvicorn backend.server:app --reload --port 8080
"""

import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agents.orchestrator import run_pipeline

app = FastAPI(title="tt_agent v3.0", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    transcript: str
    source_url: str = ""
    provider: str = "deepseek"
    api_key: str = ""
    persona: dict | None = None


@app.get("/")
async def root():
    return {"service": "tt_agent v3.0", "status": "online", "agents": 5}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Run full pipeline — returns SSE stream of agent progress."""
    async def event_stream():
        async for event in run_pipeline(
            transcript=req.transcript,
            source_url=req.source_url,
            provider=req.provider,
            api_key=req.api_key,
            persona=req.persona,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/deconstruct")
async def deconstruct_only(req: AnalyzeRequest):
    """Run only Deconstruct Agent."""
    async def event_stream():
        yield f"data: {json.dumps({'type':'start','message':'🔍 Deconstruct only'}, ensure_ascii=False)}\n\n"
        from .agents import deconstructor
        from .agents.context import AgentContext
        import uuid

        ctx = AgentContext()
        ctx.mark_start(uuid.uuid4().hex[:8])
        ctx.transcript = req.transcript

        yield f"data: {json.dumps({'type':'agent_start','agent':'deconstructor'}, ensure_ascii=False)}\n\n"
        try:
            result = await deconstructor.run(ctx, provider=req.provider, api_key=req.api_key)
            yield f"data: {json.dumps({'type':'agent_done','agent':'deconstructor','output':result}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'agent_error','error':str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
