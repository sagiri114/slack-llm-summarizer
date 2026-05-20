from slack_llm_summarizer.context import build_evidence_context
from slack_llm_summarizer.formatter import (
    format_ask_for_slack,
    format_summary_for_slack,
    format_todo_for_slack,
)
from slack_llm_summarizer.models import SlackMessage
from slack_llm_summarizer.schemas import (
    AskAnswer,
    TodoResponse,
    parse_summary_response,
    parse_todo_response,
)


def _context():
    return build_evidence_context(
        [SlackMessage(text="demo scope update", permalink="https://example.com/m1")],
        channel_id="C1",
    )


def test_parse_detailed_summary_fields() -> None:
    response = parse_summary_response(
        {
            "items": [
                {
                    "claim": "Demo scope was narrowed.",
                    "details": ["Backend API is the priority.", "Slides are deferred."],
                    "impact": "The team can finish the demo earlier.",
                    "next_steps": ["Confirm the API owner."],
                    "category": "decision",
                    "confidence": "high",
                    "sources": ["M1"],
                }
            ]
        }
    )

    item = response.decisions[0]
    assert item.details == ["Backend API is the priority.", "Slides are deferred."]
    assert item.impact == "The team can finish the demo earlier."
    assert item.next_steps == ["Confirm the API owner."]


def test_formatter_can_output_japanese_detailed_sections() -> None:
    response = parse_summary_response(
        {
            "items": [
                {
                    "claim": "Demo scope was narrowed.",
                    "details": ["Backend API is the priority."],
                    "impact": "The team can finish earlier.",
                    "next_steps": ["Confirm the owner."],
                    "category": "decision",
                    "confidence": "high",
                    "sources": ["M1"],
                }
            ]
        }
    )

    output = format_summary_for_slack(
        response,
        _context(),
        provider="deepseek",
        hours=24,
        language="ja",
    )

    assert "\u8a73\u7d30" in output
    assert "\u5f71\u97ff" in output
    assert "\u6b21\u306e\u30a2\u30af\u30b7\u30e7\u30f3" in output


def test_ask_formatter_outputs_detailed_fields() -> None:
    answer = AskAnswer(
        answer="The demo is planned for Friday.",
        confidence="high",
        sources=["M1"],
        key_findings=["Demo timing is Friday."],
        reasoning=["The message explicitly says demo is Friday."],
        next_steps=["Confirm the exact time."],
    )

    output = format_ask_for_slack(answer, _context(), language="en")

    assert "Key Findings" in output
    assert "Reasoning" in output
    assert "Next Steps" in output
    assert "Demo timing is Friday." in output


def test_todo_parser_and_formatter_output_detailed_fields() -> None:
    response: TodoResponse = parse_todo_response(
        {
            "todos": [
                {
                    "task": "Finish the backend API for the demo.",
                    "details": ["The demo depends on backend readiness."],
                    "acceptance_criteria": ["API endpoint works in the demo flow."],
                    "blockers": ["Exact API contract is not confirmed."],
                    "owner": "Bob",
                    "deadline": "Friday",
                    "status": "confirmed",
                    "confidence": "high",
                    "sources": ["M1"],
                }
            ]
        }
    )

    output = format_todo_for_slack(response, _context(), language="en")

    assert "Details" in output
    assert "Acceptance Criteria" in output
    assert "Blockers / Risks" in output
    assert "API endpoint works" in output
