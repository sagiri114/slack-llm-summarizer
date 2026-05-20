from __future__ import annotations

import sys

from slack_llm_summarizer.config import AVAILABLE_PROVIDERS, Settings
from slack_llm_summarizer.errors import ConfigurationError


def _slack_bot_token_hint() -> str:
    return (
        "缺少 SLACK_BOT_TOKEN。请在 .env 中填写从 Slack OAuth & Permissions 页面获取的 "
        "Bot User OAuth Token（格式通常为 xoxb-...）。"
    )


def _slack_app_token_hint() -> str:
    return (
        "缺少 SLACK_APP_TOKEN。请在 Slack App 后台开启 Socket Mode，并创建带 "
        "connections:write scope 的 App-Level Token（格式通常为 xapp-...）。"
    )


def _llm_key_hint(settings: Settings, provider: str) -> str:
    env_name = settings.llm_api_key_env_name(provider)  # type: ignore[arg-type]
    return (
        f"当前 LLM_PROVIDER={provider}，但没有配置 {env_name}。"
        f"请在 .env 中填写对应 API Key，或将 LLM_PROVIDER 改为已配置的 provider。"
    )


def _llm_model_hint(settings: Settings, provider: str) -> str:
    cfg = settings.provider_settings(provider)  # type: ignore[arg-type]
    if provider == "openai_compatible":
        missing = []
        if not cfg.model:
            missing.append("OPENAI_COMPATIBLE_MODEL")
        if not cfg.base_url:
            missing.append("OPENAI_COMPATIBLE_BASE_URL")
        return (
            f"LLM_PROVIDER=openai_compatible 还需要配置：{', '.join(missing)}。"
        )
    if not cfg.model:
        return f"请为 provider `{provider}` 配置模型名称环境变量。"
    return f"请为 provider `{provider}` 配置 base_url。"


def validate_slack_settings(settings: Settings) -> None:
    if not settings.slack_bot_token:
        raise ConfigurationError(_slack_bot_token_hint())
    if not settings.slack_app_token:
        raise ConfigurationError(_slack_app_token_hint())


def validate_llm_settings(
    settings: Settings,
    provider_name: str | None = None,
) -> None:
    provider = provider_name or settings.llm_provider
    if provider not in AVAILABLE_PROVIDERS:
        from slack_llm_summarizer.errors import UnknownProviderError

        raise UnknownProviderError(provider)

    if not settings.has_llm_api_key(provider):  # type: ignore[arg-type]
        raise ConfigurationError(_llm_key_hint(settings, provider))

    if not settings.is_provider_configured(provider):  # type: ignore[arg-type]
        raise ConfigurationError(_llm_model_hint(settings, provider))


def validate_startup(settings: Settings | None = None) -> Settings:
    """Validate environment; return settings on success or exit with friendly message."""
    try:
        loaded = settings or Settings.from_env()
    except ValueError as exc:
        _exit_with_error(str(exc))

    try:
        validate_slack_settings(loaded)
        validate_llm_settings(loaded)
    except ConfigurationError as exc:
        _exit_with_error(exc.user_message)
    return loaded


def _exit_with_error(message: str, *, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)
