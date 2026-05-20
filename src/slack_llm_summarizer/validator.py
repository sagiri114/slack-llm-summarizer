from __future__ import annotations

from slack_llm_summarizer.schemas import (
    AskAnswer,
    SummaryItem,
    SummaryResponse,
    TodoItem,
    TodoResponse,
)


def _valid_sources(sources: list[str], allowed: set[str]) -> list[str]:
    return [source for source in sources if source in allowed]


def _downgrade_confidence(confidence: str, *, has_valid_sources: bool) -> str:
    if has_valid_sources:
        return confidence
    return "unknown"


def validate_summary_item(item: SummaryItem, allowed: set[str]) -> SummaryItem:
    valid = _valid_sources(item.sources, allowed)
    return SummaryItem(
        claim=item.claim,
        category=item.category,
        confidence=_downgrade_confidence(item.confidence, has_valid_sources=bool(valid)),  # type: ignore[arg-type]
        sources=valid,
    )


def validate_summary_response(
    response: SummaryResponse,
    allowed: set[str],
) -> SummaryResponse:
    def _validate_items(items: list[SummaryItem]) -> list[SummaryItem]:
        validated: list[SummaryItem] = []
        for item in items:
            cleaned = validate_summary_item(item, allowed)
            if cleaned.sources or cleaned.confidence == "unknown":
                validated.append(cleaned)
            else:
                validated.append(
                    SummaryItem(
                        claim=cleaned.claim,
                        category=cleaned.category,
                        confidence="unknown",
                        sources=[],
                    )
                )
        return validated

    return SummaryResponse(
        important_updates=_validate_items(response.important_updates),
        decisions=_validate_items(response.decisions),
        schedules=_validate_items(response.schedules),
        todos=_validate_items(response.todos),
        open_questions=_validate_items(response.open_questions),
    )


def validate_todo_item(item: TodoItem, allowed: set[str]) -> TodoItem:
    valid = _valid_sources(item.sources, allowed)
    return TodoItem(
        task=item.task,
        owner=item.owner if valid else None,
        deadline=item.deadline if valid else None,
        status=item.status if valid else "unclear",
        confidence=_downgrade_confidence(item.confidence, has_valid_sources=bool(valid)),  # type: ignore[arg-type]
        sources=valid,
    )


def validate_todo_response(response: TodoResponse, allowed: set[str]) -> TodoResponse:
    todos: list[TodoItem] = []
    for item in response.todos:
        cleaned = validate_todo_item(item, allowed)
        if cleaned.sources or cleaned.confidence == "unknown":
            todos.append(cleaned)
        else:
            todos.append(
                TodoItem(
                    task=cleaned.task,
                    owner=None,
                    deadline=None,
                    status="unclear",
                    confidence="unknown",
                    sources=[],
                )
            )
    return TodoResponse(todos=todos)


def validate_ask_answer(answer: AskAnswer, allowed: set[str]) -> AskAnswer:
    valid = _valid_sources(answer.sources, allowed)
    unknowns = list(answer.unknowns)
    invalid_sources = [source for source in answer.sources if source not in allowed]
    if invalid_sources:
        unknowns.append(
            "部分引用无法在上下文中验证，已移除: " + ", ".join(invalid_sources)
        )
    if not valid and answer.answer and answer.confidence != "unknown":
        unknowns.append("回答缺乏可验证的 Slack 证据")
    return AskAnswer(
        answer=answer.answer if valid else (answer.answer if answer.answer else ""),
        confidence=_downgrade_confidence(answer.confidence, has_valid_sources=bool(valid)),  # type: ignore[arg-type]
        sources=valid,
        unknowns=unknowns,
    )
