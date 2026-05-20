from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None

ProviderName = Literal["openai", "gemini", "deepseek", "openai_compatible"]

AVAILABLE_PROVIDERS: tuple[str, ...] = ("openai", "gemini", "deepseek", "openai_compatible")

_PROVIDER_API_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _csv_env(name: str) -> set[str]:
    value = os.getenv(name, "")
    return {item.strip() for item in value.split(",") if item.strip()}


@dataclass(frozen=True)
class ProviderSettings:
    api_key: str
    model: str
    base_url: str | None = None


@dataclass(frozen=True)
class Settings:
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    llm_provider: ProviderName
    llm_temperature: float
    llm_max_tokens: int
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    gemini_api_key: str
    gemini_model: str
    deepseek_api_key: str
    deepseek_model: str
    deepseek_base_url: str
    openai_compatible_api_key: str
    openai_compatible_model: str
    openai_compatible_base_url: str
    default_summary_hours: int
    default_ask_hours: int
    default_todo_hours: int
    max_messages: int
    max_thread_replies: int
    max_context_chars: int
    summary_language: str
    allowed_channel_ids: set[str]

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
        if provider not in AVAILABLE_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER must be one of: {', '.join(AVAILABLE_PROVIDERS)}"
            )

        return cls(
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN", "").strip(),
            slack_app_token=os.getenv("SLACK_APP_TOKEN", "").strip(),
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET", "").strip(),
            llm_provider=provider,  # type: ignore[arg-type]
            llm_temperature=_float_env("LLM_TEMPERATURE", 0.2),
            llm_max_tokens=_int_env("LLM_MAX_TOKENS", 2000),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            openai_compatible_api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip(),
            openai_compatible_model=os.getenv("OPENAI_COMPATIBLE_MODEL", "").strip(),
            openai_compatible_base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip(),
            default_summary_hours=_int_env("DEFAULT_SUMMARY_HOURS", 24),
            default_ask_hours=_int_env("DEFAULT_ASK_HOURS", 168),
            default_todo_hours=_int_env("DEFAULT_TODO_HOURS", 168),
            max_messages=_int_env("MAX_MESSAGES", 100),
            max_thread_replies=_int_env("MAX_THREAD_REPLIES", 20),
            max_context_chars=_int_env("MAX_CONTEXT_CHARS", 24000),
            summary_language=os.getenv("SUMMARY_LANGUAGE", "zh").strip(),
            allowed_channel_ids=_csv_env("ALLOWED_CHANNEL_IDS"),
        )

    def provider_settings(self, provider_name: ProviderName | None = None) -> ProviderSettings:
        provider = provider_name or self.llm_provider
        if provider == "openai":
            return ProviderSettings(
                api_key=self.openai_api_key,
                model=self.openai_model,
                base_url=self.openai_base_url,
            )
        if provider == "gemini":
            return ProviderSettings(
                api_key=self.gemini_api_key,
                model=self.gemini_model,
            )
        if provider == "deepseek":
            return ProviderSettings(
                api_key=self.deepseek_api_key,
                model=self.deepseek_model,
                base_url=self.deepseek_base_url,
            )
        return ProviderSettings(
            api_key=self.openai_compatible_api_key,
            model=self.openai_compatible_model,
            base_url=self.openai_compatible_base_url or None,
        )

    def llm_api_key_env_name(self, provider_name: ProviderName | None = None) -> str:
        provider = provider_name or self.llm_provider
        return _PROVIDER_API_KEY_ENV[provider]

    def has_llm_api_key(self, provider_name: ProviderName | None = None) -> bool:
        return bool(self.provider_settings(provider_name).api_key)

    def is_provider_configured(self, provider_name: ProviderName) -> bool:
        cfg = self.provider_settings(provider_name)
        if not cfg.api_key:
            return False
        if provider_name == "openai_compatible":
            return bool(cfg.model and cfg.base_url)
        if provider_name == "gemini":
            return bool(cfg.model)
        return bool(cfg.model and cfg.base_url)
