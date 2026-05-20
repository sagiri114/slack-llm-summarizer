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
    normalized = language.lower().strip()
    if normalized == "zh":
        return "Write all human-readable text fields in Chinese."
    if normalized == "en":
        return "Write all human-readable text fields in English."
    if normalized == "ja":
        return "Write all human-readable text fields in Japanese."
    return "Write all human-readable text fields in Chinese."


def _system_prompt(language: str, role: str) -> str:
    return f"{role}\n{_language_instruction(language)}\n\n{_COMMON_RULES}"


def build_summary_prompt(context: EvidenceContext, *, language: str) -> tuple[str, str]:
    schema = {
        "items": [
            {
                "claim": "one detailed sentence with the key point",
                "details": ["2-4 concrete supporting details"],
                "impact": "why this matters, or null if not stated",
                "next_steps": ["explicit next actions or follow-ups"],
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
        "Be detailed enough for someone who did not read the channel to understand the context.\n"
        "For each item, write a specific claim, then add concrete details, impact, and next_steps when supported.\n"
        "Prefer 2-4 detailed items per section over many shallow bullets.\n"
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
        "answer": "detailed answer with context and caveats",
        "key_findings": ["important facts that directly answer the question"],
        "reasoning": ["how the cited messages support the answer"],
        "next_steps": ["recommended follow-ups or actions, only if supported"],
        "confidence": "high|medium|low|unknown",
        "sources": ["M1"],
        "unknowns": ["missing facts or caveats"],
    }
    system = _system_prompt(
        language,
        "You are a careful Slack Q&A assistant.",
    )
    user = (
        f"Question: {question.strip()}\n"
        "Answer only from the Slack messages below. If not found, put details in unknowns.\n"
        "Give a detailed answer with context, reasoning from the cited messages, and any caveats.\n"
        "Populate key_findings, reasoning, next_steps, and unknowns as separate arrays.\n"
        f"Return JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Context:\n"
        f"{context.format_for_prompt()}"
    )
    return system, user


def build_todo_prompt(context: EvidenceContext, *, language: str) -> tuple[str, str]:
    schema = {
        "todos": [
            {
                "task": "specific actionable task with context",
                "details": ["why this task exists and relevant context"],
                "acceptance_criteria": ["what done means, only if supported"],
                "blockers": ["dependencies, risks, or unknowns"],
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
        "Make each task description specific, including context and acceptance criteria when the messages support it.\n"
        "For each TODO, include details, acceptance_criteria, and blockers when the messages support them.\n"
        f"Return JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Context:\n"
        f"{context.format_for_prompt()}"
    )
    return system, user
