from slack_llm_summarizer.context import build_evidence_context
from slack_llm_summarizer.models import SlackMessage
from slack_llm_summarizer.prompts import (
    build_ask_prompt,
    build_summary_prompt,
    build_todo_prompt,
)


def test_summary_prompt_requires_json_and_sources() -> None:
    context = build_evidence_context(
        [
            SlackMessage(
                text="明日は10時に集合してください。",
                user_name="Matsuno",
                timestamp="2026-05-15T09:20:00+09:00",
                replies=[
                    SlackMessage(
                        text="ok",
                        user_name="Student",
                        timestamp="2026-05-15T09:25:00+09:00",
                    )
                ],
            )
        ],
        channel_id="C123",
    )
    system, user = build_summary_prompt(context, language="zh")

    assert "only using the provided Slack messages" in system
    assert "Return valid JSON only" in system
    assert "source IDs" in system
    assert "[M1]" in user
    assert "明日は10時に集合してください。" in user
    assert "ok" not in user.lower()


def test_ask_and_todo_prompts_include_rules() -> None:
    context = build_evidence_context(
        [SlackMessage(text="demo on Friday", user_name="Alice")],
        channel_id="C1",
    )
    ask_system, ask_user = build_ask_prompt("demo progress?", context, language="en")
    todo_system, todo_user = build_todo_prompt(context, language="en")

    for system, user in ((ask_system, ask_user), (todo_system, todo_user)):
        assert "only using the provided Slack messages" in system
        assert "Return valid JSON only" in system
        assert "[M1]" in user
