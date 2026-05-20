from __future__ import annotations

import httpx

from slack_llm_summarizer.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise RuntimeError("Gemini API key is not configured")
        if not model:
            raise RuntimeError("Gemini model is not configured")
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "responseMimeType": "application/json",
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected Gemini response") from exc

        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(part for part in text_parts if part).strip()
