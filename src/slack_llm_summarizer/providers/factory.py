from __future__ import annotations

from slack_llm_summarizer.config import ProviderName, Settings
from slack_llm_summarizer.errors import UnknownProviderError
from slack_llm_summarizer.providers.base import LLMProvider
from slack_llm_summarizer.providers.gemini_provider import GeminiProvider
from slack_llm_summarizer.providers.openai_compatible_provider import OpenAICompatibleChatProvider
from slack_llm_summarizer.startup import validate_llm_settings


def build_provider(settings: Settings, provider_name: ProviderName | str | None = None) -> LLMProvider:
    name: ProviderName
    if provider_name is None:
        name = settings.llm_provider
    else:
        normalized = str(provider_name).lower().strip()
        if normalized not in {"openai", "gemini", "deepseek", "openai_compatible"}:
            raise UnknownProviderError(normalized)
        name = normalized  # type: ignore[assignment]

    validate_llm_settings(settings, name)

    cfg = settings.provider_settings(name)
    temperature = settings.llm_temperature
    max_tokens = settings.llm_max_tokens

    if name == "gemini":
        return GeminiProvider(
            api_key=cfg.api_key,
            model=cfg.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    base_url = cfg.base_url or ""
    return OpenAICompatibleChatProvider(
        name=name,
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
