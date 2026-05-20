from __future__ import annotations

from slack_llm_summarizer.context import EvidenceContext
from slack_llm_summarizer.errors import ConfigurationError, UnknownProviderError
from slack_llm_summarizer.schemas import (
    AskAnswer,
    SummaryItem,
    SummaryResponse,
    TodoItem,
    TodoResponse,
)

_CATEGORY_LABELS = {
    "important_updates": "重要更新",
    "decisions": "决定",
    "schedules": "日程/截止",
    "todos": "TODO",
    "open_questions": "未解决问题",
}

_CONFIDENCE_LABELS = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "unknown",
}


def _format_source_links(context: EvidenceContext, sources: list[str]) -> str:
    if not sources:
        return "无"
    parts: list[str] = []
    for source_id in sources:
        permalink = context.permalink_for(source_id)
        if permalink:
            parts.append(f"<{permalink}|{source_id}>")
        else:
            parts.append(source_id)
    return ", ".join(parts)


def _format_item_block(item: SummaryItem, context: EvidenceContext) -> str:
    lines = [
        f"• {item.claim}",
        f"  证据: {_format_source_links(context, item.sources)}",
        f"  置信度: {_CONFIDENCE_LABELS.get(item.confidence, item.confidence)}",
    ]
    return "\n".join(lines)


def format_summary_for_slack(
    response: SummaryResponse,
    context: EvidenceContext,
    *,
    provider: str,
    hours: int,
) -> str:
    header = f"*AI Summary* `range:{hours}h` `provider:{provider}`"
    sections: list[str] = [header]
    buckets = [
        ("important_updates", response.important_updates),
        ("decisions", response.decisions),
        ("schedules", response.schedules),
        ("todos", response.todos),
        ("open_questions", response.open_questions),
    ]
    has_content = False
    for key, items in buckets:
        if not items:
            continue
        has_content = True
        label = _CATEGORY_LABELS[key]
        sections.append(f"\n*{label}*")
        for item in items:
            prefix = ""
            if key == "todos" and item.category == "todo":
                prefix = "[todo] "
            sections.append(_format_item_block(item, context).replace("• ", f"• {prefix}", 1))
    if not has_content:
        sections.append("\n未找到可总结的内容。")
    return "\n".join(sections)


def format_ask_for_slack(answer: AskAnswer, context: EvidenceContext) -> str:
    lines = ["*Answer*", answer.answer or "未知"]
    lines.append("\n*Evidence*")
    if answer.sources:
        for source_id in answer.sources:
            permalink = context.permalink_for(source_id)
            if permalink:
                lines.append(f"• <{permalink}|{source_id}>")
            else:
                lines.append(f"• {source_id}")
    else:
        lines.append("• 无")

    lines.append("\n*Unknown / Not found*")
    if answer.unknowns:
        for unknown in answer.unknowns:
            lines.append(f"• {unknown}")
    elif answer.confidence == "unknown" or not answer.sources:
        lines.append("• 没有找到足够的 Slack 证据")
    else:
        lines.append("• 无")
    lines.append(f"\n置信度: {_CONFIDENCE_LABELS.get(answer.confidence, answer.confidence)}")
    return "\n".join(lines)


def format_todo_for_slack(response: TodoResponse, context: EvidenceContext) -> str:
    lines = ["*TODOs*"]
    if not response.todos:
        lines.append("• 未找到明确的 TODO")
        return "\n".join(lines)
    for item in response.todos:
        owner = item.owner or "未指定"
        deadline = item.deadline or "未指定"
        lines.append(
            f"• [{item.status}] {owner}: {item.task}，截止 {deadline}\n"
            f"  证据: {_format_source_links(context, item.sources)}\n"
            f"  confidence: {_CONFIDENCE_LABELS.get(item.confidence, item.confidence)}"
        )
    return "\n".join(lines)


def format_error_for_slack(error: Exception) -> str:
    if isinstance(error, ConfigurationError):
        return f"处理失败：{error.user_message}"
    if isinstance(error, UnknownProviderError):
        return f"处理失败：{error.user_message}"

    message = str(error).lower()
    if "api key is not configured" in message or "not configured" in message:
        return (
            "处理失败：LLM 未配置完整。请检查 .env 中的 LLM_PROVIDER 与对应 API Key，"
            "或运行 `python -m slack_llm_summarizer.check_provider` 诊断。"
        )
    if "invalid json" in message or "returned invalid json" in message:
        return "处理失败：LLM 返回格式异常，请稍后重试。"
    return "处理失败：请稍后重试，或联系维护者查看日志。"
