from slack_llm_summarizer.options import (
    format_available_providers,
    parse_options,
    parse_time_range,
    strip_option_tokens,
)


def test_parse_provider_deepseek() -> None:
    options = parse_options(
        "24h provider:deepseek",
        default_hours=24,
        default_max_messages=100,
    )
    assert options.provider == "deepseek"
    assert options.invalid_provider is None


def test_parse_invalid_provider() -> None:
    options = parse_options(
        "provider:foo 24h",
        default_hours=24,
        default_max_messages=100,
    )
    assert options.provider is None
    assert options.invalid_provider == "foo"


def test_ask_time_range_and_provider() -> None:
    opts = parse_time_range(
        "7d provider:gemini",
        default_hours=168,
        default_max_messages=100,
    )
    assert opts.hours == 168
    assert opts.provider == "gemini"


def test_strip_option_tokens_keeps_question() -> None:
    assert strip_option_tokens("provider:deepseek 最近 demo 进展 7d") == "最近 demo 进展"


def test_format_available_providers_lists_all() -> None:
    text = format_available_providers()
    assert "openai" in text
    assert "openai_compatible" in text
