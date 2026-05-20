from slack_llm_summarizer.context import build_evidence_context
from slack_llm_summarizer.models import SlackMessage


def test_filters_empty_and_low_value_replies() -> None:
    context = build_evidence_context(
        [
            SlackMessage(text="We should finish the demo by Friday.", user_name="Alice"),
            SlackMessage(
                text="Backend update",
                user_name="Bob",
                replies=[
                    SlackMessage(text="ok", user_name="Carol"),
                    SlackMessage(text="I can handle the backend part.", user_name="Bob"),
                ],
            ),
            SlackMessage(text="", user_name="Ghost"),
        ],
        channel_id="C123",
    )

    texts = {message.text for message in context.messages}
    assert "We should finish the demo by Friday." in texts
    assert "I can handle the backend part." in texts
    assert "ok" not in texts
    assert context.by_id["M1"].source_id == "M1"
    assert "T2-R2" in context.by_id


def test_source_ids_and_thread_grouping() -> None:
    context = build_evidence_context(
        [
            SlackMessage(
                text="Parent",
                replies=[SlackMessage(text="Reply one", user_name="A")],
            )
        ],
        channel_id="C1",
    )

    assert context.messages[0].source_id == "M1"
    assert context.messages[1].source_id == "T1-R1"
    assert context.messages[1].parent_source_id == "M1"


def test_truncates_by_max_chars() -> None:
    messages = [
        SlackMessage(text=f"Message {index} " + ("x" * 200), user_name="User")
        for index in range(10)
    ]
    context = build_evidence_context(messages, channel_id="C1", max_chars=500)
    assert len(context.messages) < 10
    assert len(context.format_for_prompt()) <= 500 + 200
