"""Backward-compatible re-exports. Prefer `slack_llm_summarizer.providers`."""

from slack_llm_summarizer.providers import LLMProvider, build_provider

__all__ = ["LLMProvider", "build_provider"]
