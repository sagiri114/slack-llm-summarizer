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

_LABELS = {
    "zh": {
        "summary_header": "AI 详细总结",
        "important_updates": "重要更新",
        "decisions": "决定事项",
        "schedules": "日程 / 截止",
        "todos": "TODO",
        "open_questions": "未解决问题",
        "details": "详情",
        "impact": "影响",
        "next_steps": "下一步",
        "evidence": "证据",
        "confidence": "置信度",
        "none": "无",
        "no_summary": "未找到可总结的内容。",
        "answer": "回答",
        "key_findings": "关键依据",
        "reasoning": "推理过程",
        "unknown": "未知 / 未确认",
        "not_found": "没有找到足够的 Slack 证据。",
        "owner": "负责人",
        "deadline": "截止",
        "status": "状态",
        "acceptance_criteria": "完成标准",
        "blockers": "阻塞点 / 风险",
        "unassigned": "未指定",
        "no_todos": "未找到明确的 TODO",
        "failed": "处理失败",
        "check_config": "LLM 未配置完整。请检查 .env 中的 LLM_PROVIDER 与对应 API Key，或运行 `python -m slack_llm_summarizer.check_provider` 诊断。",
        "invalid_json": "LLM 返回格式异常，请稍后重试。",
        "generic_error": "请稍后重试，或联系维护者查看日志。",
    },
    "ja": {
        "summary_header": "AI 詳細サマリー",
        "important_updates": "重要な更新",
        "decisions": "決定事項",
        "schedules": "日程 / 締切",
        "todos": "TODO",
        "open_questions": "未解決事項",
        "details": "詳細",
        "impact": "影響",
        "next_steps": "次のアクション",
        "evidence": "根拠",
        "confidence": "信頼度",
        "none": "なし",
        "no_summary": "要約できる内容は見つかりませんでした。",
        "answer": "回答",
        "key_findings": "主な根拠",
        "reasoning": "判断理由",
        "unknown": "不明 / 未確認",
        "not_found": "十分な Slack 上の根拠が見つかりませんでした。",
        "owner": "担当者",
        "deadline": "締切",
        "status": "状態",
        "acceptance_criteria": "完了条件",
        "blockers": "ブロッカー / リスク",
        "unassigned": "未指定",
        "no_todos": "明確な TODO は見つかりませんでした",
        "failed": "処理に失敗しました",
        "check_config": "LLM の設定が不完全です。.env の LLM_PROVIDER と対応する API Key を確認するか、`python -m slack_llm_summarizer.check_provider` を実行してください。",
        "invalid_json": "LLM の返却形式が不正です。しばらくしてから再試行してください。",
        "generic_error": "しばらくしてから再試行するか、ログを確認してください。",
    },
    "en": {
        "summary_header": "Detailed AI Summary",
        "important_updates": "Important Updates",
        "decisions": "Decisions",
        "schedules": "Schedule / Deadlines",
        "todos": "TODO",
        "open_questions": "Open Questions",
        "details": "Details",
        "impact": "Impact",
        "next_steps": "Next Steps",
        "evidence": "Evidence",
        "confidence": "Confidence",
        "none": "none",
        "no_summary": "No summarizable content found.",
        "answer": "Answer",
        "key_findings": "Key Findings",
        "reasoning": "Reasoning",
        "unknown": "Unknown / Not confirmed",
        "not_found": "No sufficient Slack evidence was found.",
        "owner": "Owner",
        "deadline": "Deadline",
        "status": "Status",
        "acceptance_criteria": "Acceptance Criteria",
        "blockers": "Blockers / Risks",
        "unassigned": "Unassigned",
        "no_todos": "No explicit TODOs found",
        "failed": "Failed",
        "check_config": "LLM is not fully configured. Check LLM_PROVIDER and the matching API key in .env, or run `python -m slack_llm_summarizer.check_provider`.",
        "invalid_json": "LLM returned an invalid format. Please retry later.",
        "generic_error": "Please retry later or ask a maintainer to check logs.",
    },
}

_CONFIDENCE_LABELS = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "unknown",
}


def _labels(language: str = "zh") -> dict[str, str]:
    normalized = language.lower().strip()
    if normalized not in _LABELS:
        normalized = "zh"
    return _LABELS[normalized]


def _format_source_links(context: EvidenceContext, sources: list[str], *, language: str = "zh") -> str:
    labels = _labels(language)
    if not sources:
        return labels["none"]
    parts: list[str] = []
    for source_id in sources:
        permalink = context.permalink_for(source_id)
        if permalink:
            parts.append(f"<{permalink}|{source_id}>")
        else:
            parts.append(source_id)
    return ", ".join(parts)


def _format_list(label: str, values: list[str]) -> list[str]:
    if not values:
        return []
    lines = [f"  *{label}:*"]
    lines.extend(f"    - {value}" for value in values)
    return lines


def _format_item_block(item: SummaryItem, context: EvidenceContext, *, language: str = "zh") -> str:
    labels = _labels(language)
    lines = [f"- *{item.claim}*"]
    lines.extend(_format_list(labels["details"], item.details))
    if item.impact:
        lines.append(f"  *{labels['impact']}:* {item.impact}")
    lines.extend(_format_list(labels["next_steps"], item.next_steps))
    lines.append(f"  *{labels['evidence']}:* {_format_source_links(context, item.sources, language=language)}")
    lines.append(f"  *{labels['confidence']}:* {_CONFIDENCE_LABELS.get(item.confidence, item.confidence)}")
    return "\n".join(lines)


def format_summary_for_slack(
    response: SummaryResponse,
    context: EvidenceContext,
    *,
    provider: str,
    hours: int,
    language: str = "zh",
) -> str:
    labels = _labels(language)
    header = f"*{labels['summary_header']}* `range:{hours}h` `provider:{provider}`"
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
        sections.append(f"\n*{labels[key]}*")
        for item in items:
            sections.append(_format_item_block(item, context, language=language))
    if not has_content:
        sections.append(f"\n{labels['no_summary']}")
    return "\n".join(sections)


def format_ask_for_slack(
    answer: AskAnswer,
    context: EvidenceContext,
    *,
    language: str = "zh",
) -> str:
    labels = _labels(language)
    lines = [f"*{labels['answer']}*", answer.answer or labels["unknown"]]
    for label, values in (
        (labels["key_findings"], answer.key_findings),
        (labels["reasoning"], answer.reasoning),
        (labels["next_steps"], answer.next_steps),
    ):
        section = _format_list(label, values)
        if section:
            lines.extend(["", *section])
    lines.append(f"\n*{labels['evidence']}*")
    if answer.sources:
        for source_id in answer.sources:
            permalink = context.permalink_for(source_id)
            if permalink:
                lines.append(f"- <{permalink}|{source_id}>")
            else:
                lines.append(f"- {source_id}")
    else:
        lines.append(f"- {labels['none']}")

    lines.append(f"\n*{labels['unknown']}*")
    if answer.unknowns:
        for unknown in answer.unknowns:
            lines.append(f"- {unknown}")
    elif answer.confidence == "unknown" or not answer.sources:
        lines.append(f"- {labels['not_found']}")
    else:
        lines.append(f"- {labels['none']}")
    lines.append(f"\n*{labels['confidence']}:* {_CONFIDENCE_LABELS.get(answer.confidence, answer.confidence)}")
    return "\n".join(lines)


def _format_todo_item(item: TodoItem, context: EvidenceContext, *, language: str) -> str:
    labels = _labels(language)
    owner = item.owner or labels["unassigned"]
    deadline = item.deadline or labels["unassigned"]
    lines = [f"- *{item.task}*"]
    lines.extend(_format_list(labels["details"], item.details))
    lines.extend(_format_list(labels["acceptance_criteria"], item.acceptance_criteria))
    lines.extend(_format_list(labels["blockers"], item.blockers))
    lines.extend(
        [
            f"  *{labels['owner']}:* {owner}",
            f"  *{labels['deadline']}:* {deadline}",
            f"  *{labels['status']}:* {item.status}",
            f"  *{labels['evidence']}:* {_format_source_links(context, item.sources, language=language)}",
            f"  *{labels['confidence']}:* {_CONFIDENCE_LABELS.get(item.confidence, item.confidence)}",
        ]
    )
    return "\n".join(lines)


def format_todo_for_slack(
    response: TodoResponse,
    context: EvidenceContext,
    *,
    language: str = "zh",
) -> str:
    labels = _labels(language)
    lines = [f"*{labels['todos']}*"]
    if not response.todos:
        lines.append(f"- {labels['no_todos']}")
        return "\n".join(lines)
    for item in response.todos:
        lines.append(_format_todo_item(item, context, language=language))
    return "\n".join(lines)


def format_error_for_slack(error: Exception, *, language: str = "zh") -> str:
    labels = _labels(language)
    if isinstance(error, ConfigurationError):
        return f"{labels['failed']}: {error.user_message}"
    if isinstance(error, UnknownProviderError):
        return f"{labels['failed']}: {error.user_message}"

    message = str(error).lower()
    if "api key is not configured" in message or "not configured" in message:
        return f"{labels['failed']}: {labels['check_config']}"
    if "invalid json" in message or "returned invalid json" in message:
        return f"{labels['failed']}: {labels['invalid_json']}"
    return f"{labels['failed']}: {labels['generic_error']}"
