import pytest

from slack_llm_summarizer.config import Settings
from slack_llm_summarizer.errors import ConfigurationError, UnknownProviderError
from slack_llm_summarizer.providers import build_provider
from slack_llm_summarizer.providers.openai_compatible_provider import OpenAICompatibleChatProvider


def test_build_openai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com/v1")
    settings = Settings.from_env()
    provider = build_provider(settings, "openai")
    assert isinstance(provider, OpenAICompatibleChatProvider)
    assert provider.name == "openai"
    assert provider.model == "gpt-test"


def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    settings = Settings.from_env()
    with pytest.raises(UnknownProviderError):
        build_provider(settings, "unknown-vendor")


def test_openai_compatible_requires_model_and_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "k")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "")
    settings = Settings.from_env()
    with pytest.raises(ConfigurationError):
        build_provider(settings, "openai_compatible")
