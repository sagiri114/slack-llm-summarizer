import pytest

from slack_llm_summarizer.config import AVAILABLE_PROVIDERS, Settings
from slack_llm_summarizer.errors import ConfigurationError
from slack_llm_summarizer.startup import validate_llm_settings, validate_slack_settings


def test_available_providers() -> None:
    assert "openai_compatible" in AVAILABLE_PROVIDERS
    assert len(AVAILABLE_PROVIDERS) == 4


def test_slack_missing_bot_token_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test")
    settings = Settings.from_env()
    with pytest.raises(ConfigurationError) as exc:
        validate_slack_settings(settings)
    assert "SLACK_BOT_TOKEN" in exc.value.user_message


def test_llm_missing_key_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    settings = Settings.from_env()
    with pytest.raises(ConfigurationError) as exc:
        validate_llm_settings(settings, "openai")
    assert "OPENAI_API_KEY" in exc.value.user_message
