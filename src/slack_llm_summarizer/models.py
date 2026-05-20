from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SlackMessage:
    text: str
    user_id: str | None = None
    user_name: str | None = None
    timestamp: str | None = None
    thread_ts: str | None = None
    permalink: str | None = None
    channel_id: str | None = None
    slack_ts: str | None = None
    subtype: str | None = None
    replies: list["SlackMessage"] = field(default_factory=list)

