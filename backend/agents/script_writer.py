"""Script Agent — TikTok script adaptation with creator constraints."""

from .context import AgentContext
from .llm import call_llm
import re

SYSTEM_PROMPT = """You are a TikTok creative director. You adapt viral video structures into original scripts for small business creators.
Rules:
- Output must be shootable with just a smartphone — no professional equipment
- Scripts must feel authentic, not over-produced
- Every script gets a shot-by-shot filming guide
- Hook must land within first 3 seconds — no warm-up, no intro
- Respect FTC guidelines for product claims
- CTA optimized for TikTok (comment → follow → Shop)"""

SCRIPT_CONSTRAINTS = """
Creator Constraints:
1. Solo creator or 1 helper — no film crew
2. iPhone / Android camera only — no DSLR, no lighting kit
3. Natural light or existing room light — no studio setup
4. Filming location: their actual store/workspace — no sets
5. Language: conversational, authentic, like talking to one person
6. Hook MUST land in first 3 seconds — no intro, no "hey guys welcome back"
7. Captions: large text, key words highlighted, readable on mobile
8. CTA: natural, not pushy — "drop a comment if..." or "save this for later" or "tap the yellow bag"
"""

FILMING_GUIDE = """
Shot-by-Shot Filming Instructions (include in every script):
| Time | Shot Type | Camera | Action | Audio/Text |
- Shot Types: Close-up (product fills frame), Medium (waist-up), Wide (full store/setup)
- Camera: Locked (tripod/stable surface), Slow Push (handheld, slowly move closer), Pan (smooth horizontal)
- Lighting: Natural window light or room lights — no additional equipment
- Audio: Original voiceover OR trending TikTok sound (suggest which)
"""


def build_prompt(ctx: AgentContext) -> str:
    decon_raw = ctx.deconstruction.get("raw", "") if ctx.deconstruction else ""
    brand = ctx.persona.get("brand", "Your Brand")
    niche = ctx.persona.get("niche", "small business")

    return f"""Adapt this viral video structure into an original TikTok script for {brand}.

CONTEXT:
- Brand: {brand}
- Niche: {niche}
- Creator: Solo, smartphone-only, authentic style

ORIGINAL TRANSCRIPT (for reference):
{ctx.transcript[:600]}

DECONSTRUCTION:
{decon_raw[:1200]}

{SCRIPT_CONSTRAINTS}

{FILMING_GUIDE}

OUTPUT FORMAT:
## Script Overview
- Hook Type:
- Structure:
- Target Duration:
- Recommended Sound (TikTok trending or original audio):

## Shot-by-Shot Script
| Time | Shot Type | Camera Move | Visual | Voiceover | On-Screen Text |

## Filming Checklist
- [ ] Props needed (list specific items)
- [ ] Best filming location in the store
- [ ] Lighting time (best natural light window)
- [ ] Wardrobe suggestion (what to wear)

## Full Voiceover Script
(One continuous read)

## Caption + Hashtags
Caption (under 150 chars):
Hashtags (1 trending + 2 niche + 2 broad):
"""


async def run(ctx: AgentContext, provider: str = "deepseek", api_key: str = "") -> str:
    ctx.mark_agent("script_writer")
    try:
        result = await call_llm(
            build_prompt(ctx),
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
            api_key=api_key,
        )
        ctx.script = result

        # Extract filming checklist
        film_match = re.search(r'##\s*Filming Checklist[\s\S]*?(?=##\s|$)', result)
        ctx.filming_guide = film_match.group(0).strip() if film_match else "See shot-by-shot table above."
        return result
    except Exception as e:
        ctx.add_error("script_writer", str(e))
        raise
