from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SummaryCategory = Literal[
    "important_update",
    "decision",
    "schedule",
    "todo",
    "open_question",
]
Confidence = Literal["high", "medium", "low", "unknown"]
TodoStatus = Literal["confirmed", "proposed", "unclear"]


@dataclass
class SummaryItem:
    claim: str
    category: SummaryCategory
    confidence: Confidence
    sources: list[str] = field(default_factory=list)


@dataclass
class TodoItem:
    task: str
    owner: str | None
    deadline: str | None
    status: TodoStatus
    confidence: Confidence
    sources: list[str] = field(default_factory=list)


@dataclass
class AskAnswer:
    answer: str
    confidence: Confidence
    sources: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


@dataclass
class SummaryResponse:
    important_updates: list[SummaryItem] = field(default_factory=list)
    decisions: list[SummaryItem] = field(default_factory=list)
    schedules: list[SummaryItem] = field(default_factory=list)
    todos: list[SummaryItem] = field(default_factory=list)
    open_questions: list[SummaryItem] = field(default_factory=list)


@dataclass
class TodoResponse:
    todos: list[TodoItem] = field(default_factory=list)


CATEGORY_FIELD_MAP: dict[SummaryCategory, str] = {
    "important_update": "important_updates",
    "decision": "decisions",
    "schedule": "schedules",
    "todo": "todos",
    "open_question": "open_questions",
}


def _confidence(value: Any) -> Confidence:
    if value in {"high", "medium", "low", "unknown"}:
        return value
    return "unknown"


def _todo_status(value: Any) -> TodoStatus:
    if value in {"confirmed", "proposed", "unclear"}:
        return value
    return "unclear"


def _category(value: Any) -> SummaryCategory | None:
    if value in CATEGORY_FIELD_MAP:
        return value
    return None


def parse_summary_item(raw: dict[str, Any]) -> SummaryItem | None:
    category = _category(raw.get("category"))
    claim = str(raw.get("claim", "")).strip()
    if not category or not claim:
        return None
    sources = raw.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    return SummaryItem(
        claim=claim,
        category=category,
        confidence=_confidence(raw.get("confidence")),
        sources=[str(s) for s in sources],
    )


def parse_summary_response(data: dict[str, Any]) -> SummaryResponse:
    response = SummaryResponse()
    items = data.get("items")
    if isinstance(items, list):
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = parse_summary_item(raw)
            if item is None:
                continue
            field_name = CATEGORY_FIELD_MAP[item.category]
            getattr(response, field_name).append(item)
        return response

    for field_name in CATEGORY_FIELD_MAP.values():
        bucket = data.get(field_name)
        if not isinstance(bucket, list):
            continue
        for raw in bucket:
            if not isinstance(raw, dict):
                continue
            claim = str(raw.get("claim", "")).strip()
            if not claim:
                continue
            category_key = next(
                (k for k, v in CATEGORY_FIELD_MAP.items() if v == field_name),
                "important_update",
            )
            sources = raw.get("sources") or []
            if not isinstance(sources, list):
                sources = []
            getattr(response, field_name).append(
                SummaryItem(
                    claim=claim,
                    category=category_key,
                    confidence=_confidence(raw.get("confidence")),
                    sources=[str(s) for s in sources],
                )
            )
    return response


def parse_todo_item(raw: dict[str, Any]) -> TodoItem | None:
    task = str(raw.get("task", "")).strip()
    if not task:
        return None
    owner = raw.get("owner")
    deadline = raw.get("deadline")
    sources = raw.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    return TodoItem(
        task=task,
        owner=str(owner).strip() if owner else None,
        deadline=str(deadline).strip() if deadline else None,
        status=_todo_status(raw.get("status")),
        confidence=_confidence(raw.get("confidence")),
        sources=[str(s) for s in sources],
    )


def parse_todo_response(data: dict[str, Any]) -> TodoResponse:
    response = TodoResponse()
    todos = data.get("todos")
    if not isinstance(todos, list):
        return response
    for raw in todos:
        if not isinstance(raw, dict):
            continue
        item = parse_todo_item(raw)
        if item:
            response.todos.append(item)
    return response


def parse_ask_answer(data: dict[str, Any]) -> AskAnswer:
    answer = str(data.get("answer", "")).strip()
    sources = data.get("sources") or []
    unknowns = data.get("unknowns") or []
    if not isinstance(sources, list):
        sources = []
    if not isinstance(unknowns, list):
        unknowns = []
    return AskAnswer(
        answer=answer,
        confidence=_confidence(data.get("confidence")),
        sources=[str(s) for s in sources],
        unknowns=[str(u) for u in unknowns],
    )
