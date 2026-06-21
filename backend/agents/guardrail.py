"""Guardrail Agent — TikTok policy + FTC compliance check."""

from .context import AgentContext

# TikTok Community Guidelines violations
TIKTOK_POLICY_FLAGS = [
    ("guaranteed results", "TikTok policy: avoid absolute claims about results"),
    ("guaranteed income", "TikTok policy: income claims require disclaimer"),
    ("cure", "TikTok policy: health claims require substantiation"),
    ("miracle", "TikTok policy: avoid exaggerated claims"),
    ("risk-free", "TikTok policy: financial/product claims must be accurate"),
]

# FTC endorsement guidelines
FTC_ISSUES = [
    ("#ad", "FTC: sponsored content must disclose partnership"),
    ("#sponsored", "FTC: clear disclosure required for paid promotions"),
    ("free product", "FTC: product seeding must be disclosed if reviewing"),
]

# Creator authenticity flags
CREATOR_ISSUES = [
    ("literally changed my life", "Over-hype: dilute for authenticity"),
    ("you NEED this", "Over-hype: suggest instead of command"),
    ("EVERYONE is sleeping on", "Over-hype: overused TikTok trope"),
    ("this is INSANE", "Over-hype: consider toning down"),
]


def check(text: str) -> list[dict]:
    """Run TikTok policy + FTC + authenticity checks."""
    issues = []
    text_lower = text.lower()

    for phrase, explanation in TIKTOK_POLICY_FLAGS:
        if phrase in text_lower:
            issues.append({
                "type": "tiktok_policy",
                "severity": "fail",
                "message": f"{explanation}",
            })

    for phrase, explanation in FTC_ISSUES:
        if phrase in text_lower:
            issues.append({
                "type": "ftc",
                "severity": "warn",
                "message": f"{explanation}",
            })

    for phrase, explanation in CREATOR_ISSUES:
        if phrase in text_lower:
            issues.append({
                "type": "authenticity",
                "severity": "warn",
                "message": f"{explanation}",
            })

    # Check hook density (first 100 chars should hook immediately)
    first_words = text.split()[:30]
    first_text = " ".join(first_words).lower()
    hook_triggers = ["imagine", "watch this", "the truth about", "stop", "i found", "why", "how to"]
    if not any(trigger in first_text for trigger in hook_triggers):
        issues.append({
            "type": "hook",
            "severity": "warn",
            "message": "Hook may be weak — consider leading with a curiosity trigger or pattern interrupt",
        })

    return issues


async def run(ctx: AgentContext) -> list[dict]:
    """Run Guardrail Agent on generated script."""
    ctx.mark_agent("guardrail")
    text = ctx.script or ctx.transcript or ""
    issues = check(text)
    ctx.guardrail_issues = issues
    return issues


def format_report(issues: list[dict]) -> str:
    if not issues:
        return "All checks passed"
    lines = ["Guardrail Report:"]
    for i in issues:
        emoji = "❌" if i["severity"] == "fail" else "⚠️"
        lines.append(f"  {emoji} [{i['type']}] {i['message']}")
    return "\n".join(lines)
