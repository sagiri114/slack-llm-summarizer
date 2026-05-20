from __future__ import annotations

import json

from slack_llm_summarizer.context import EvidenceContext

_COMMON_RULES = """
Rules:
- You must answer only using the provided Slack messages.
- Do not use outside knowledge.
- Every important claim must cite one or more source IDs.
- Use only source IDs that appear in the context.
- If evidence is insufficient, say unknown.
- Do not infer owner, deadline, or decision unless explicitly supported.
- Distinguish confirmed decisions, proposals, and open questions.
- Return valid JSON only. No Markdown.
- Do not output Slack permalinks or URLs; only source IDs in "sources".
""".strip()


def _language_instruction(language: str) -> str:
    if language == "zh":
        return "Write human-readable text fields in 中文."
    if language == "en":
        return "Write human-readable text fields in English."
    return "Write human-readable text fields in 日本語."


def _system_prompt(language: str, role: str) -> str:
    return f"{role}\n{_language_instruction(language)}\n\n{_COMMON_RULES}"


def build_summary_prompt(context: EvidenceContext, *, language: str) -> tuple[str, str]:
    schema = {
        "items": [
            {
                "claim": "string",
                "category": "important_update|decision|schedule|todo|open_question",
                "confidence": "high|medium|low|unknown",
                "sources": ["M1"],
            }
        ]
    }
    system = _system_prompt(
        language,
        "You are a careful Slack channel summarization assistant.",
    )
    user = (
        "Summarize the Slack messages below.\n"
        "Extract important updates, decisions, schedules/deadlines, TODOs, and open questions.\n"
        f"Return JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Context:\n"
        f"{context.format_for_prompt()}"
    )
    return system, user


def build_ask_prompt(
    question: str,
    context: EvidenceContext,
    *,
    language: str,
) -> tuple[str, str]:
    schema = {
        "answer": "string",
        "confidence": "high|medium|low|unknown",
        "sources": ["M1"],
        "unknowns": ["string"],
    }
    system = _system_prompt(
        language,
        "You are a careful Slack Q&A assistant.",
    )
    user = (
        f"Question: {question.strip()}\n"
        "Answer only from the Slack messages below. If not found, put details in unknowns.\n"
        f"Return JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Context:\n"
        f"{context.format_for_prompt()}"
    )
    return system, user


def build_todo_prompt(context: EvidenceContext, *, language: str) -> tuple[str, str]:
    schema = {
        "todos": [
            {
                "task": "string",
                "owner": "string or null",
                "deadline": "string or null",
                "status": "confirmed|proposed|unclear",
                "confidence": "high|medium|low|unknown",
                "sources": ["M1"],
            }
        ]
    }
    system = _system_prompt(
        language,
        "You are a careful Slack TODO extraction assistant.",
    )
    user = (
        "Extract actionable TODOs from the Slack messages below.\n"
        "Only include tasks explicitly mentioned or clearly assigned.\n"
        f"Return JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Context:\n"
        f"{context.format_for_prompt()}"
    )
    return system, user
