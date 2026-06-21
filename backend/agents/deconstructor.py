"""Deconstruct Agent — 5-Layer Viral Video Analysis (TikTok-optimized)."""

from .context import AgentContext
from .llm import call_llm

SYSTEM_PROMPT = """You are a senior TikTok content strategist. You reverse-engineer viral videos into reproducible frameworks.
Respond in English. Be concise. Use Markdown. Focus on actionable insights, not flattery."""

HOOK_PATTERNS = [
    "Pattern Interrupt (unexpected visual first 0.5s)",
    "Curiosity Gap (open question with no immediate answer)",
    "Value First (lead with result, explain later)",
    "Identity Hook (target a specific group: sneakerheads, busy moms, etc.)",
    "Trending Audio (script annotated with recommended sound match)",
    "Controversy/Contrarian (unpopular opinion that grabs attention)",
]

STRUCTURE_TYPES = [
    "Contrast Burst (15-30s): Hook→Reveal→Detail→CTA",
    "Educational Loop (30-60s): Hook→Problem→Solution→Proof→CTA",
    "Story Arc (45-90s): Setup→Conflict→Resolution→Lesson→CTA",
    "Product Showcase (15-45s): Result→Features→Social Proof→CTA",
]


def build_prompt(ctx: AgentContext) -> str:
    return f"""Perform a 5-layer deconstruction of this TikTok video transcript.

{ctx.transcript[:3000]}

Output (Markdown):

## 1. Hook Analysis
Which hook pattern was used? (choose from: {', '.join(HOOK_PATTERNS[:4])})
Why did it work? What emotion did it trigger in the first 3 seconds?

## 2. Structure Breakdown
| Time | Function | Visual | Audio/Text | Retention Score (1-5) |
Map to closest structure: {', '.join(STRUCTURE_TYPES[:3])}

## 3. Emotional Arc
- 0-25%: What does the viewer feel?
- 25-75%: How does the emotion shift?
- 75-100%: What's the emotional takeaway?

## 4. Speaking Rhythm
- Avg sentence length (short <8 / medium 8-15 / long >15 words)
- Pause pattern (where does the creator pause for effect?)
- Energy shifts (where does tone change?)

## 5. Viral Hypothesis (MOST IMPORTANT — FALSIFIABLE)
This video went viral because ___. If true, then when we apply this to a different niche, we should see ___.
What's ONE reason this might NOT work in another context?"""


async def run(ctx: AgentContext, provider: str = "deepseek", api_key: str = "") -> str:
    ctx.mark_agent("deconstructor")
    try:
        result = await call_llm(
            build_prompt(ctx),
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
        )
        ctx.deconstruction = {"raw": result, "agent": "deconstructor"}
        return result
    except Exception as e:
        ctx.add_error("deconstructor", str(e))
        raise
