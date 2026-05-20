from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from slack_llm_summarizer.providers.json_utils import parse_json_dict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    model: str
    base_url: str | None = None


class LLMProvider(ABC):
    name: str
    model: str
    base_url: str | None = None

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, model=self.model, base_url=self.base_url)

    @abstractmethod
    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        raw = await self.complete_text(system_prompt, user_prompt)
        try:
            return parse_json_dict(raw)
        except Exception as exc:
            logger.exception("Failed to parse LLM JSON response from %s", self.name)
            raise RuntimeError("LLM returned invalid JSON") from exc
