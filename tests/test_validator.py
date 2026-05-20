from slack_llm_summarizer.schemas import AskAnswer, SummaryItem, SummaryResponse, TodoItem, TodoResponse
from slack_llm_summarizer.validator import (
    validate_ask_answer,
    validate_summary_response,
    validate_todo_response,
)


def test_summary_without_sources_is_downgraded() -> None:
    response = SummaryResponse(
        important_updates=[
            SummaryItem(
                claim="Demo on Friday",
                category="important_update",
                confidence="high",
                sources=[],
            )
        ]
    )
    validated = validate_summary_response(response, {"M1"})
    item = validated.important_updates[0]
    assert item.confidence == "unknown"
    assert item.sources == []


def test_invalid_source_ids_removed() -> None:
    response = SummaryResponse(
        decisions=[
            SummaryItem(
                claim="Use OpenAI",
                category="decision",
                confidence="high",
                sources=["M1", "M99"],
            )
        ]
    )
    validated = validate_summary_response(response, {"M1"})
    assert validated.decisions[0].sources == ["M1"]


def test_ask_invalid_sources_move_to_unknowns() -> None:
    answer = AskAnswer(
        answer="Friday",
        confidence="high",
        sources=["M9"],
        unknowns=[],
    )
    validated = validate_ask_answer(answer, {"M1"})
    assert validated.sources == []
    assert validated.confidence == "unknown"
    assert any("M9" in item for item in validated.unknowns)


def test_todo_keeps_valid_sources() -> None:
    response = TodoResponse(
        todos=[
            TodoItem(
                task="Finish API",
                owner="Bob",
                deadline="Friday",
                status="confirmed",
                confidence="high",
                sources=["M2"],
            )
        ]
    )
    validated = validate_todo_response(response, {"M1", "M2"})
    assert validated.todos[0].sources == ["M2"]
    assert validated.todos[0].confidence == "high"
