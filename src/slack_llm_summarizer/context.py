from __future__ import annotations

import re
from dataclasses import dataclass, field

from slack_llm_summarizer.models import SlackMessage

_SYSTEM_SUBTYPES = frozenset(
    {
        "channel_join",
        "channel_leave",
        "group_join",
        "group_leave",
        "join",
        "leave",
        "bot_message",
    }
)

_LOW_VALUE_REPLIES = frozenset(
    {
        "ok",
        "okay",
        "k",
        "kk",
        "thanks",
        "thank you",
        "thx",
        "ty",
        "+1",
        "👍",
        "了解",
        "承知",
        "承知しました",
        "わかりました",
        "分かりました",
        "got it",
        "sure",
        "yes",
        "no",
        "yep",
        "nope",
        "lol",
        "haha",
    }
)

_EMOJI_ONLY = re.compile(
    r"^[\s\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F"
    r"\U0001F1E0-\U0001F1FF0-9#*_,.!?;:()\[\]{}<>+=\-/\\|@$%^&~`'\"]+$"
)


@dataclass(frozen=True)
class EvidenceMessage:
    source_id: str
    text: str
    user_name: str | None
    timestamp: str | None
    permalink: str | None
    channel_id: str
    thread_ts: str | None
    slack_ts: str | None
    parent_source_id: str | None = None


@dataclass
class EvidenceContext:
    messages: list[EvidenceMessage] = field(default_factory=list)
    by_id: dict[str, EvidenceMessage] = field(default_factory=dict)

    @property
    def source_ids(self) -> set[str]:
        return set(self.by_id.keys())

    def format_for_prompt(self) -> str:
        blocks: list[str] = []
        for message in self.messages:
            link_line = "available" if message.permalink else "unavailable"
            blocks.append(f"[{message.source_id}]")
            blocks.append(f"time: {message.timestamp or 'unknown'}")
            blocks.append(f"user: {message.user_name or 'unknown'}")
            blocks.append(f"link: {link_line}")
            blocks.append(f"text: {message.text}")
            blocks.append("")
        return "\n".join(blocks).strip()

    def permalink_for(self, source_id: str) -> str | None:
        message = self.by_id.get(source_id)
        return message.permalink if message else None


def _normalize_text(text: str) -> str:
    return text.replace("\u00a0", " ").strip()


def _is_low_value_reply(text: str) -> bool:
    normalized = _normalize_text(text).lower().rstrip(".。!！?？")
    if not normalized:
        return True
    if normalized in _LOW_VALUE_REPLIES:
        return True
    if len(normalized) <= 3 and normalized.isalpha():
        return True
    if _EMOJI_ONLY.match(normalized):
        return True
    return False


def _should_skip_message(
    message: SlackMessage,
    *,
    bot_user_id: str | None,
    bot_id: str | None,
    subtype: str | None,
    is_reply: bool,
) -> bool:
    text = _normalize_text(message.text)
    if not text:
        return True
    if subtype and subtype in _SYSTEM_SUBTYPES:
        return True
    if message.user_id and bot_user_id and message.user_id == bot_user_id:
        return True
    if message.user_id and message.user_id.startswith("B") and bot_id:
        return True
    if is_reply and _is_low_value_reply(text):
        return True
    return False


def build_evidence_context(
    raw_messages: list[SlackMessage],
    *,
    channel_id: str,
    bot_user_id: str | None = None,
    bot_id: str | None = None,
    max_chars: int | None = None,
) -> EvidenceContext:
    context = EvidenceContext()
    seen_text_keys: set[tuple[str, str, str]] = set()
    parent_index = 0

    for parent in raw_messages:
        parent_index += 1
        parent_id = f"M{parent_index}"
        parent_key = (parent_id, parent.timestamp or "", _normalize_text(parent.text))
        if not _should_skip_message(
            parent,
            bot_user_id=bot_user_id,
            bot_id=bot_id,
            subtype=getattr(parent, "subtype", None),
            is_reply=False,
        ):
            if parent_key not in seen_text_keys:
                seen_text_keys.add(parent_key)
                evidence = EvidenceMessage(
                    source_id=parent_id,
                    text=_normalize_text(parent.text),
                    user_name=parent.user_name,
                    timestamp=parent.timestamp,
                    permalink=parent.permalink,
                    channel_id=channel_id,
                    thread_ts=parent.thread_ts or parent.slack_ts,
                    slack_ts=parent.slack_ts,
                )
                context.messages.append(evidence)
                context.by_id[parent_id] = evidence

        reply_index = 0
        for reply in parent.replies:
            reply_index += 1
            reply_id = f"T{parent_index}-R{reply_index}"
            if _should_skip_message(
                reply,
                bot_user_id=bot_user_id,
                bot_id=bot_id,
                subtype=getattr(reply, "subtype", None),
                is_reply=True,
            ):
                continue
            reply_key = (reply_id, reply.timestamp or "", _normalize_text(reply.text))
            if reply_key in seen_text_keys:
                continue
            seen_text_keys.add(reply_key)
            evidence = EvidenceMessage(
                source_id=reply_id,
                text=_normalize_text(reply.text),
                user_name=reply.user_name,
                timestamp=reply.timestamp,
                permalink=reply.permalink,
                channel_id=channel_id,
                thread_ts=reply.thread_ts or parent.thread_ts or parent.slack_ts,
                slack_ts=reply.slack_ts,
                parent_source_id=parent_id if parent_id in context.by_id else None,
            )
            context.messages.append(evidence)
            context.by_id[reply_id] = evidence

    if max_chars is not None and max_chars > 0:
        _truncate_context(context, max_chars)
    return context


def _truncate_context(context: EvidenceContext, max_chars: int) -> None:
    kept: list[EvidenceMessage] = []
    kept_ids: set[str] = set()
    total = 0
    for message in context.messages:
        block = (
            f"[{message.source_id}]\n"
            f"time: {message.timestamp or 'unknown'}\n"
            f"user: {message.user_name or 'unknown'}\n"
            f"link: {'available' if message.permalink else 'unavailable'}\n"
            f"text: {message.text}\n"
        )
        if total + len(block) > max_chars and kept:
            break
        kept.append(message)
        kept_ids.add(message.source_id)
        total += len(block)
    context.messages = kept
    context.by_id = {message.source_id: message for message in kept}


def merge_contexts(*contexts: EvidenceContext) -> EvidenceContext:
    merged = EvidenceContext()
    seen: set[str] = set()
    for ctx in contexts:
        for message in ctx.messages:
            if message.source_id in seen:
                continue
            seen.add(message.source_id)
            merged.messages.append(message)
            merged.by_id[message.source_id] = message
    return merged
