from __future__ import annotations


class ConfigurationError(RuntimeError):
    """Raised when required environment configuration is missing or invalid."""

    def __init__(self, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(user_message)


class UnknownProviderError(ConfigurationError):
    def __init__(self, provider: str) -> None:
        from slack_llm_summarizer.config import AVAILABLE_PROVIDERS

        joined = ", ".join(AVAILABLE_PROVIDERS)
        super().__init__(
            f"未知的 LLM provider：`{provider}`。可用选项：{joined}。"
            f"请在命令中使用 provider:openai 等形式，或在 .env 中设置 LLM_PROVIDER。"
        )
