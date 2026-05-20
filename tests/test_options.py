from slack_llm_summarizer.options import (
    parse_mention_command,
    parse_options,
    parse_time_range,
    strip_option_tokens,
)


def test_parse_duration_provider_and_max_messages() -> None:
    options = parse_options(
        "provider:gemini 7d max:40",
        default_hours=24,
        default_max_messages=100,
    )

    assert options.provider == "gemini"
    assert options.invalid_provider is None
    assert options.hours == 168
    assert options.max_messages == 40


def test_parse_uses_defaults() -> None:
    options = parse_options("", default_hours=24, default_max_messages=100)

    assert options.provider is None
    assert options.hours == 24
    assert options.max_messages == 100


def test_parse_time_range_for_todo() -> None:
    options = parse_time_range("7d", default_hours=168, default_max_messages=100)
    assert options.hours == 168


def test_strip_option_tokens_from_question() -> None:
    assert strip_option_tokens("最近 demo 进展 7d provider:openai") == "最近 demo 进展"


def test_parse_mention_commands() -> None:
    assert parse_mention_command("<@U1> summary 24h") == parse_mention_command("summary 24h")
    parsed = parse_mention_command("<@U1> ask 最近 demo 谁负责？")
    assert parsed is not None
    assert parsed.command == "ask"
    assert "demo" in parsed.args
