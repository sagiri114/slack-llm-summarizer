from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from slack_sdk.web.async_client import AsyncWebClient

from slack_llm_summarizer.config import Settings
from slack_llm_summarizer.context import build_evidence_context
from slack_llm_summarizer.errors import ConfigurationError, UnknownProviderError
from slack_llm_summarizer.formatter import (
    format_ask_for_slack,
    format_error_for_slack,
    format_summary_for_slack,
    format_todo_for_slack,
)
from slack_llm_summarizer.options import (
    extract_ask_question,
    format_available_providers,
    parse_options,
    parse_time_range,
)
from slack_llm_summarizer.prompts import (
    build_ask_prompt,
    build_summary_prompt,
    build_todo_prompt,
)
from slack_llm_summarizer.providers import build_provider
from slack_llm_summarizer.retrieval import retrieve_for_question
from slack_llm_summarizer.schemas import parse_ask_answer, parse_summary_response, parse_todo_response
from slack_llm_summarizer.slack_history import SlackHistoryReader
from slack_llm_summarizer.validator import (
    validate_ask_answer,
    validate_summary_response,
    validate_todo_response,
)

logger = logging.getLogger(__name__)
RespondFn = Callable[[str], Awaitable[None]]


class AgentCommands:
    def __init__(self, settings: Settings, client: AsyncWebClient) -> None:
        self.settings = settings
        self.client = client
        self._bot_user_id: str | None = None

    async def _ensure_bot_user_id(self) -> str | None:
        if self._bot_user_id is not None:
            return self._bot_user_id
        try:
            auth = await self.client.auth_test()
            self._bot_user_id = auth.get("user_id")
        except Exception:
            logger.exception("Failed to resolve bot user id")
        return self._bot_user_id

    def _channel_allowed(self, channel_id: str) -> bool:
        if not self.settings.allowed_channel_ids:
            return True
        return channel_id in self.settings.allowed_channel_ids

    def _invalid_provider_message(self, provider: str) -> str:
        return (
            f"未知的 provider：`{provider}`。可用选项：{format_available_providers()}。"
            f"示例：`/summary 24h provider:deepseek`"
        )

    async def _fetch_context(self, *, channel_id: str, hours: int, max_messages: int):
        reader = SlackHistoryReader(
            self.client,
            max_thread_replies=self.settings.max_thread_replies,
        )
        raw_messages = await reader.fetch_recent_messages(
            channel_id=channel_id,
            hours=hours,
            max_messages=max_messages,
        )
        bot_user_id = await self._ensure_bot_user_id()
        context = build_evidence_context(
            raw_messages,
            channel_id=channel_id,
            bot_user_id=bot_user_id,
            max_chars=self.settings.max_context_chars,
        )
        return context

    async def handle_summary(
        self,
        *,
        channel_id: str,
        text: str,
        respond: RespondFn,
    ) -> None:
        if not self._channel_allowed(channel_id):
            await respond("此频道未在允许列表中，无法处理。")
            return

        options = parse_options(
            text,
            default_hours=self.settings.default_summary_hours,
            default_max_messages=self.settings.max_messages,
        )
        if options.invalid_provider:
            await respond(self._invalid_provider_message(options.invalid_provider))
            return

        await respond(
            f"正在处理 summary... `range:{options.hours}h` `max:{options.max_messages}`"
        )

        try:
            context = await self._fetch_context(
                channel_id=channel_id,
                hours=options.hours,
                max_messages=options.max_messages,
            )
            if not context.messages:
                await respond("指定范围内没有可分析的消息。")
                return

            provider = build_provider(self.settings, options.provider)
            system_prompt, user_prompt = build_summary_prompt(
                context,
                language=self.settings.summary_language,
            )
            data = await provider.complete_json(system_prompt, user_prompt)
            validated = validate_summary_response(
                parse_summary_response(data),
                context.source_ids,
            )
            await respond(
                format_summary_for_slack(
                    validated,
                    context,
                    provider=provider.name,
                    hours=options.hours,
                    language=self.settings.summary_language,
                )
            )
        except (ConfigurationError, UnknownProviderError) as exc:
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))
        except Exception as exc:
            logger.exception("Failed to handle /summary")
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))

    async def handle_ask(
        self,
        *,
        channel_id: str,
        text: str,
        respond: RespondFn,
    ) -> None:
        if not self._channel_allowed(channel_id):
            await respond("此频道未在允许列表中，无法处理。")
            return

        question = extract_ask_question(text)
        if not question:
            await respond("请提供问题，例如：`/ask 最近 demo 的进展是什么？`")
            return

        time_opts = parse_time_range(
            text,
            default_hours=self.settings.default_ask_hours,
            default_max_messages=self.settings.max_messages,
        )
        if time_opts.invalid_provider:
            await respond(self._invalid_provider_message(time_opts.invalid_provider))
            return

        await respond(f"正在分析问题... `range:{time_opts.hours}h`")

        try:
            full_context = await self._fetch_context(
                channel_id=channel_id,
                hours=time_opts.hours,
                max_messages=time_opts.max_messages,
            )
            if not full_context.messages:
                await respond("指定范围内没有可分析的消息。")
                return

            context = retrieve_for_question(
                full_context,
                question,
                max_chars=self.settings.max_context_chars,
            )
            provider = build_provider(self.settings, time_opts.provider)
            system_prompt, user_prompt = build_ask_prompt(
                question,
                context,
                language=self.settings.summary_language,
            )
            data = await provider.complete_json(system_prompt, user_prompt)
            validated = validate_ask_answer(
                parse_ask_answer(data),
                context.source_ids,
            )
            await respond(
                format_ask_for_slack(
                    validated,
                    context,
                    language=self.settings.summary_language,
                )
            )
        except (ConfigurationError, UnknownProviderError) as exc:
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))
        except Exception as exc:
            logger.exception("Failed to handle /ask")
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))

    async def handle_todo(
        self,
        *,
        channel_id: str,
        text: str,
        respond: RespondFn,
    ) -> None:
        if not self._channel_allowed(channel_id):
            await respond("此频道未在允许列表中，无法处理。")
            return

        time_opts = parse_time_range(
            text,
            default_hours=self.settings.default_todo_hours,
            default_max_messages=self.settings.max_messages,
        )
        if time_opts.invalid_provider:
            await respond(self._invalid_provider_message(time_opts.invalid_provider))
            return

        await respond(f"正在提取 TODO... `range:{time_opts.hours}h`")

        try:
            context = await self._fetch_context(
                channel_id=channel_id,
                hours=time_opts.hours,
                max_messages=time_opts.max_messages,
            )
            if not context.messages:
                await respond("指定范围内没有可分析的消息。")
                return

            provider = build_provider(self.settings, time_opts.provider)
            system_prompt, user_prompt = build_todo_prompt(
                context,
                language=self.settings.summary_language,
            )
            data = await provider.complete_json(system_prompt, user_prompt)
            validated = validate_todo_response(
                parse_todo_response(data),
                context.source_ids,
            )
            await respond(
                format_todo_for_slack(
                    validated,
                    context,
                    language=self.settings.summary_language,
                )
            )
        except (ConfigurationError, UnknownProviderError) as exc:
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))
        except Exception as exc:
            logger.exception("Failed to handle /todo")
            await respond(format_error_for_slack(exc, language=self.settings.summary_language))
