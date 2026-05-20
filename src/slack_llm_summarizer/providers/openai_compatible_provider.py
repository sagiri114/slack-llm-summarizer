from __future__ import annotations

import httpx

from slack_llm_summarizer.providers.base import LLMProvider


class OpenAICompatibleChatProvider(LLMProvider):
    """OpenAI-style chat/completions API (OpenAI, DeepSeek, custom gateways)."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise RuntimeError(f"{name} API key is not configured")
        if not model:
            raise RuntimeError(f"{name} model is not configured")
        if not base_url:
            raise RuntimeError(f"{name} base_url is not configured")
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected {self.name} response") from exc
        return str(content).strip()
