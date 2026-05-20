from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from slack_llm_summarizer.config import AVAILABLE_PROVIDERS, Settings
from slack_llm_summarizer.context import build_evidence_context
from slack_llm_summarizer.formatter import format_summary_for_slack
from slack_llm_summarizer.models import SlackMessage
from slack_llm_summarizer.prompts import build_summary_prompt
from slack_llm_summarizer.providers import build_provider
from slack_llm_summarizer.schemas import parse_summary_response
from slack_llm_summarizer.startup import validate_llm_settings
from slack_llm_summarizer.validator import validate_summary_response


def _load_messages(path: Path) -> list[SlackMessage]:
    raw_items = json.loads(path.read_text(encoding="utf-8"))
    messages: list[SlackMessage] = []
    for item in raw_items:
        replies = [
            SlackMessage(
                text=reply["text"],
                user_name=reply.get("user_name"),
                user_id=reply.get("user_id"),
                timestamp=reply.get("timestamp"),
                permalink=reply.get("permalink"),
            )
            for reply in item.get("replies", [])
        ]
        messages.append(
            SlackMessage(
                text=item["text"],
                user_name=item.get("user_name"),
                user_id=item.get("user_id"),
                timestamp=item.get("timestamp"),
                permalink=item.get("permalink"),
                replies=replies,
            )
        )
    return messages


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run summary without Slack.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--provider", choices=list(AVAILABLE_PROVIDERS), default=None)
    parser.add_argument("--channel-id", default="dry-run")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    settings = Settings.from_env()
    validate_llm_settings(settings, args.provider)

    messages = _load_messages(args.input)
    context = build_evidence_context(
        messages,
        channel_id=args.channel_id,
        max_chars=settings.max_context_chars,
    )
    provider = build_provider(settings, args.provider)
    system_prompt, user_prompt = build_summary_prompt(
        context,
        language=settings.summary_language,
    )
    data = await provider.complete_json(system_prompt, user_prompt)
    validated = validate_summary_response(parse_summary_response(data), context.source_ids)
    print(
        format_summary_for_slack(
            validated,
            context,
            provider=provider.name,
            hours=args.hours,
            language=settings.summary_language,
        )
    )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
