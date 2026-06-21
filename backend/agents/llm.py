"""
Multi-provider LLM client with streaming support.
Supports: DeepSeek, StepFun (阶跃星辰), OpenAI-compatible.
"""

import os, json, httpx
from typing import AsyncIterator

PROVIDERS = {
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "stepfun": {
        "url": "https://api.stepfun.com/v1/chat/completions",
        "model": "step-3.7-flash",
        "env_key": "STEPFUN_API_KEY",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
}


def get_api_key(provider: str) -> str:
    """Get API key from environment or config."""
    conf = PROVIDERS.get(provider, {})
    return os.getenv(conf.get("env_key", ""), "")


async def call_llm(
    prompt: str,
    system_prompt: str = "",
    provider: str = "deepseek",
    api_key: str = "",
    stream: bool = False,
) -> str:
    """Call LLM and return full response."""
    key = api_key or get_api_key(provider)
    if not key:
        raise ValueError(f"No API key for {provider}")

    conf = PROVIDERS.get(provider, PROVIDERS["deepseek"])
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            conf["url"],
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={
                "model": conf["model"],
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000,
                "stream": stream,
            },
        )
        resp.raise_for_status()

        if stream:
            full = []
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            full.append(delta)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
            return "".join(full)
        else:
            data = resp.json()
            return data["choices"][0]["message"]["content"]


async def call_llm_stream(
    prompt: str,
    system_prompt: str = "",
    provider: str = "deepseek",
    api_key: str = "",
) -> AsyncIterator[str]:
    """Call LLM with streaming, yielding tokens."""
    key = api_key or get_api_key(provider)
    if not key:
        raise ValueError(f"No API key for {provider}")

    conf = PROVIDERS.get(provider, PROVIDERS["deepseek"])
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            conf["url"],
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={
                "model": conf["model"],
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
