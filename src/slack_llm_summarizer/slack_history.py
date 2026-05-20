from __future__ import annotations

import datetime as dt
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient

from slack_llm_summarizer.models import SlackMessage


def _ts_to_datetime(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        seconds = float(ts)
    except ValueError:
        return None
    return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc).isoformat()


def _clean_text(text: str | None) -> str:
    return (text or "").replace("\u00a0", " ").strip()


class SlackHistoryReader:
    def __init__(self, client: AsyncWebClient, *, max_thread_replies: int) -> None:
        self.client = client
        self.max_thread_replies = max_thread_replies
        self._user_cache: dict[str, str] = {}

    async def fetch_recent_messages(
        self,
        *,
        channel_id: str,
        hours: int,
        max_messages: int,
    ) -> list[SlackMessage]:
        oldest = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)).timestamp()
        response = await self.client.conversations_history(
            channel=channel_id,
            oldest=str(oldest),
            inclusive=True,
            limit=max_messages,
        )
        raw_messages = list(response.get("messages", []))
        raw_messages.reverse()

        messages: list[SlackMessage] = []
        for raw in raw_messages:
            text = _clean_text(raw.get("text"))
            if not text:
                continue

            ts = raw.get("ts")
            user_id = raw.get("user") or raw.get("bot_id")
            replies = await self._fetch_replies(channel_id=channel_id, parent=raw)
            messages.append(
                SlackMessage(
                    text=text,
                    user_id=user_id,
                    user_name=await self._user_name(user_id),
                    timestamp=_ts_to_datetime(ts),
                    thread_ts=raw.get("thread_ts"),
                    permalink=await self._permalink(channel_id, ts),
                    channel_id=channel_id,
                    slack_ts=ts,
                    subtype=raw.get("subtype"),
                    replies=replies,
                )
            )
        return messages

    async def _fetch_replies(self, *, channel_id: str, parent: dict[str, Any]) -> list[SlackMessage]:
        reply_count = int(parent.get("reply_count") or 0)
        thread_ts = parent.get("thread_ts") or parent.get("ts")
        if reply_count <= 0 or not thread_ts:
            return []

        response = await self.client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=self.max_thread_replies + 1,
        )
        raw_replies = list(response.get("messages", []))[1:]

        replies: list[SlackMessage] = []
        for raw in raw_replies[: self.max_thread_replies]:
            text = _clean_text(raw.get("text"))
            if not text:
                continue
            user_id = raw.get("user") or raw.get("bot_id")
            reply_ts = raw.get("ts")
            replies.append(
                SlackMessage(
                    text=text,
                    user_id=user_id,
                    user_name=await self._user_name(user_id),
                    timestamp=_ts_to_datetime(reply_ts),
                    thread_ts=thread_ts,
                    permalink=await self._permalink(channel_id, reply_ts),
                    channel_id=channel_id,
                    slack_ts=reply_ts,
                    subtype=raw.get("subtype"),
                )
            )
        return replies

    async def _user_name(self, user_id: str | None) -> str | None:
        if not user_id or user_id.startswith("B"):
            return user_id
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            response = await self.client.users_info(user=user_id)
            user = response.get("user", {})
            profile = user.get("profile", {})
            name = profile.get("real_name") or user.get("real_name") or user.get("name") or user_id
        except Exception:
            name = user_id
        self._user_cache[user_id] = name
        return name

    async def _permalink(self, channel_id: str, ts: str | None) -> str | None:
        if not ts:
            return None
        try:
            response = await self.client.chat_getPermalink(channel=channel_id, message_ts=ts)
            return response.get("permalink")
        except Exception:
            return None

