from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from kb_core.config import settings

PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


class LLMClient:
    """轻量 LLM HTTP 客户端，支持 DeepSeek/OpenAI 兼容 API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        provider: str | None = None,
    ) -> None:
        """Initialize from explicit params, falling back to env config."""
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = base_url or PROVIDER_BASE_URLS.get(
            provider or settings.llm_provider, "https://api.deepseek.com/v1"
        )

    @classmethod
    def from_config(cls, config: dict) -> "LLMClient":
        """Create client from a DB LLMConfig dict."""
        return cls(
            api_key=config.get("api_key_encrypted"),
            model=config.get("model"),
            base_url=config.get("base_url") or PROVIDER_BASE_URLS.get(config.get("provider", "deepseek")),
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
    )
    async def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
    )
    async def chat_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """返回 JSON 格式响应."""
        result = await self.chat(prompt, system_prompt)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1]
            result = result.rsplit("```", 1)[0]
        return json.loads(result.strip())

    async def chat_stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """异步流式调用 LLM，逐个 yield content token。"""
        async for event in self.chat_stream_detailed(prompt, system_prompt):
            if event["type"] == "content":
                yield event["text"]

    async def chat_stream_detailed(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """异步流式调用 LLM，yield {"type": "reasoning"|"content", "text": str}。"""
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.1,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    line_data = line[6:].strip()
                    if not line_data or line_data == "[DONE]":
                        continue
                    chunk = json.loads(line_data)
                    delta = chunk["choices"][0].get("delta", {})
                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        yield {"type": "reasoning", "text": reasoning}
                    content = delta.get("content")
                    if content:
                        yield {"type": "content", "text": content}
