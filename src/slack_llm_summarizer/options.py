from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from slack_llm_summarizer.config import AVAILABLE_PROVIDERS, ProviderName

CommandName = Literal["summary", "ask", "todo"]


@dataclass(frozen=True)
class SummaryOptions:
    hours: int
    max_messages: int
    provider: ProviderName | None = None
    invalid_provider: str | None = None


@dataclass(frozen=True)
class TimeRangeOptions:
    hours: int
    max_messages: int
    provider: ProviderName | None = None
    invalid_provider: str | None = None


@dataclass(frozen=True)
class MentionCommand:
    command: CommandName
    args: str


def format_available_providers() -> str:
    return ", ".join(AVAILABLE_PROVIDERS)


def _parse_duration_token(token: str, *, hours: int) -> int:
    match = re.fullmatch(r"(\d+)([hd])", token)
    if not match:
        return hours
    amount = int(match.group(1))
    unit = match.group(2)
    return amount if unit == "h" else amount * 24


def _parse_common_tokens(
    text: str,
    *,
    default_hours: int,
    default_max_messages: int,
) -> tuple[int, int, ProviderName | None, str | None]:
    normalized = text.strip().lower()
    hours = default_hours
    max_messages = default_max_messages
    provider: ProviderName | None = None
    invalid_provider: str | None = None

    for token in normalized.split():
        if token.startswith("provider:"):
            value = token.split(":", 1)[1].strip().lower()
            if value in AVAILABLE_PROVIDERS:
                provider = value  # type: ignore[assignment]
            else:
                invalid_provider = value
            continue
        if token.startswith("max:"):
            value = token.split(":", 1)[1]
            if value.isdigit():
                max_messages = max(1, int(value))
            continue
        hours = _parse_duration_token(token, hours=hours)

    return max(1, hours), max(1, max_messages), provider, invalid_provider


def parse_options(text: str, *, default_hours: int, default_max_messages: int) -> SummaryOptions:
    hours, max_messages, provider, invalid_provider = _parse_common_tokens(
        text,
        default_hours=default_hours,
        default_max_messages=default_max_messages,
    )
    return SummaryOptions(
        hours=hours,
        max_messages=max_messages,
        provider=provider,
        invalid_provider=invalid_provider,
    )


def parse_time_range(text: str, *, default_hours: int, default_max_messages: int) -> TimeRangeOptions:
    hours, max_messages, provider, invalid_provider = _parse_common_tokens(
        text,
        default_hours=default_hours,
        default_max_messages=default_max_messages,
    )
    return TimeRangeOptions(
        hours=hours,
        max_messages=max_messages,
        provider=provider,
        invalid_provider=invalid_provider,
    )


def _args_after_keyword(text: str, keywords: tuple[str, ...]) -> str:
    for keyword in keywords:
        match = re.search(
            rf"(?:^|\s){re.escape(keyword)}(?:\s+(.+))?$",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return (match.group(1) or "").strip()
    return ""


def parse_mention_command(text: str) -> MentionCommand | None:
    normalized = re.sub(r"<@[^>]+>", "", text).strip()
    if not normalized:
        return None
    lowered = normalized.lower()

    if "要約" in normalized:
        return MentionCommand(command="summary", args=_args_after_keyword(normalized, ("要約",)))

    for keywords, command in (
        (("ask",), "ask"),
        (("todo",), "todo"),
        (("summary", "summarize"), "summary"),
    ):
        for keyword in keywords:
            if re.search(rf"(?:^|\s){re.escape(keyword)}(?:\s|$)", lowered):
                cmd: CommandName = command  # type: ignore[assignment]
                return MentionCommand(command=cmd, args=_args_after_keyword(normalized, keywords))
    return None


def strip_option_tokens(text: str) -> str:
    tokens: list[str] = []
    for token in text.split():
        lowered = token.lower()
        if lowered.startswith("provider:") or lowered.startswith("max:"):
            continue
        if re.fullmatch(r"(\d+)([hd])", lowered):
            continue
        tokens.append(token)
    return " ".join(tokens).strip()


def extract_ask_question(text: str) -> str:
    return strip_option_tokens(text)
