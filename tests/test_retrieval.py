from slack_llm_summarizer.context import EvidenceContext, EvidenceMessage
from slack_llm_summarizer.retrieval import extract_keywords, retrieve_for_question


def _message(
    source_id: str,
    text: str,
    *,
    parent: str | None = None,
) -> EvidenceMessage:
    return EvidenceMessage(
        source_id=source_id,
        text=text,
        user_name="user",
        timestamp="2026-05-19T10:00:00Z",
        permalink=f"https://example.com/{source_id}",
        channel_id="C1",
        thread_ts=None,
        slack_ts=None,
        parent_source_id=parent,
    )


def test_extract_keywords_filters_stopwords() -> None:
    keywords = extract_keywords("最近 demo Friday 的进展是什么")
    assert "demo" in keywords
    assert "friday" in keywords
    assert "最近" not in keywords


def test_retrieve_demo_friday_messages() -> None:
    full = EvidenceContext(
        messages=[
            _message("M1", "Team lunch on Monday"),
            _message("M2", "We should finish the demo by Friday."),
            _message("M3", "Unrelated budget discussion"),
        ],
        by_id={},
    )
    full.by_id = {message.source_id: message for message in full.messages}

    subset = retrieve_for_question(full, "demo Friday", max_chars=5000)
    texts = {message.text for message in subset.messages}
    assert "We should finish the demo by Friday." in texts
    assert "Team lunch on Monday" not in texts


def test_retrieve_reply_includes_thread() -> None:
    full = EvidenceContext(
        messages=[
            _message("M1", "Plan the demo"),
            _message("T1-R1", "Friday works for demo", parent="M1"),
            _message("T1-R2", "I will prepare slides", parent="M1"),
        ],
        by_id={},
    )
    full.by_id = {message.source_id: message for message in full.messages}

    subset = retrieve_for_question(full, "Friday demo", max_chars=5000)
    ids = {message.source_id for message in subset.messages}
    assert "M1" in ids
    assert "T1-R1" in ids
    assert "T1-R2" in ids
