from __future__ import annotations

import asyncio
import logging

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from slack_llm_summarizer.commands import AgentCommands
from slack_llm_summarizer.options import parse_mention_command
from slack_llm_summarizer.startup import validate_startup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(settings) -> AsyncApp:
    app = AsyncApp(token=settings.slack_bot_token)
    commands = AgentCommands(settings, app.client)

    @app.command("/summary")
    async def handle_summary_command(ack, body, respond) -> None:
        await ack()
        await commands.handle_summary(
            channel_id=body["channel_id"],
            text=body.get("text", ""),
            respond=respond,
        )

    @app.command("/ask")
    async def handle_ask_command(ack, body, respond) -> None:
        await ack()
        await commands.handle_ask(
            channel_id=body["channel_id"],
            text=body.get("text", ""),
            respond=respond,
        )

    @app.command("/todo")
    async def handle_todo_command(ack, body, respond) -> None:
        await ack()
        await commands.handle_todo(
            channel_id=body["channel_id"],
            text=body.get("text", ""),
            respond=respond,
        )

    @app.event("app_mention")
    async def handle_app_mention(event, say) -> None:
        text = event.get("text", "")
        parsed = parse_mention_command(text)
        if parsed is None:
            return

        async def respond(message: str) -> None:
            await say(text=message, thread_ts=event.get("ts"))

        if parsed.command == "summary":
            await commands.handle_summary(
                channel_id=event["channel"],
                text=parsed.args,
                respond=respond,
            )
        elif parsed.command == "ask":
            await commands.handle_ask(
                channel_id=event["channel"],
                text=parsed.args,
                respond=respond,
            )
        else:
            await commands.handle_todo(
                channel_id=event["channel"],
                text=parsed.args,
                respond=respond,
            )

    return app


async def async_main() -> None:
    settings = validate_startup()
    app = create_app(settings)
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)
    logger.info(
        "Starting Slack AI Agent (provider=%s, model=%s)",
        settings.llm_provider,
        settings.provider_settings().model,
    )
    await handler.start_async()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
