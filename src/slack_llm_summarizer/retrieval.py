from __future__ import annotations

import re
from collections.abc import Iterable

from slack_llm_summarizer.context import EvidenceContext, EvidenceMessage, merge_contexts

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "who",
        "when",
        "where",
        "why",
        "how",
        "which",
        "this",
        "that",
        "these",
        "those",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "with",
        "from",
        "by",
        "about",
        "最近",
        "什么",
        "谁",
        "怎么",
        "如何",
        "是否",
        "吗",
        "呢",
        "的",
        "了",
        "在",
        "是",
        "有",
        "和",
        "与",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+", re.IGNORECASE)


def extract_keywords(question: str) -> list[str]:
    tokens = [token.lower() for token in _TOKEN_RE.findall(question)]
    keywords: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 2 or token in _STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _message_score(message: EvidenceMessage, keywords: Iterable[str]) -> int:
    haystack = f"{message.text} {message.user_name or ''}".lower()
    return sum(1 for keyword in keywords if keyword in haystack)


def _thread_source_ids(context: EvidenceContext, parent_id: str) -> list[str]:
    ids: list[str] = []
    if parent_id in context.by_id:
        ids.append(parent_id)
    if not parent_id.startswith("M"):
        return ids
    prefix = f"T{parent_id[1:]}-R"
    for message in context.messages:
        if message.source_id.startswith(prefix) or message.parent_source_id == parent_id:
            if message.source_id not in ids:
                ids.append(message.source_id)
    return ids


def retrieve_for_question(
    full_context: EvidenceContext,
    question: str,
    *,
    max_chars: int,
) -> EvidenceContext:
    keywords = extract_keywords(question)
    if not keywords:
        subset = EvidenceContext(
            messages=list(full_context.messages),
            by_id=dict(full_context.by_id),
        )
        _truncate_by_chars(subset, max_chars)
        return subset

    scored: list[tuple[int, EvidenceMessage]] = []
    for message in full_context.messages:
        score = _message_score(message, keywords)
        if score > 0:
            scored.append((score, message))

    if not scored:
        subset = EvidenceContext(
            messages=list(full_context.messages[-20:]),
            by_id={m.source_id: m for m in full_context.messages[-20:]},
        )
        _truncate_by_chars(subset, max_chars)
        return subset

    scored.sort(key=lambda item: (-item[0], full_context.messages.index(item[1])))
    selected_ids: set[str] = set()
    for _, message in scored:
        if message.source_id.startswith("T") and "-R" in message.source_id:
            parent_id = message.parent_source_id
            if parent_id:
                selected_ids.update(_thread_source_ids(full_context, parent_id))
            else:
                thread_num = message.source_id.split("-", 1)[0][1:]
                parent_id = f"M{thread_num}"
                if parent_id in full_context.by_id:
                    selected_ids.update(_thread_source_ids(full_context, parent_id))
                else:
                    selected_ids.add(message.source_id)
        elif message.source_id.startswith("M"):
            selected_ids.update(_thread_source_ids(full_context, message.source_id))
        else:
            selected_ids.add(message.source_id)

    ordered: list[EvidenceMessage] = []
    for message in full_context.messages:
        if message.source_id in selected_ids:
            ordered.append(message)

    subset = EvidenceContext(messages=ordered, by_id={m.source_id: m for m in ordered})
    _truncate_by_chars(subset, max_chars)
    return subset


def _truncate_by_chars(context: EvidenceContext, max_chars: int) -> None:
    if max_chars <= 0:
        return
    total = len(context.format_for_prompt())
    while total > max_chars and len(context.messages) > 1:
        context.messages.pop()
        context.by_id = {m.source_id: m for m in context.messages}
        total = len(context.format_for_prompt())
