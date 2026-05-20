"""Backward-compatible re-exports. Prefer `slack_llm_summarizer.prompts`."""

from slack_llm_summarizer.prompts import (
    build_ask_prompt,
    build_summary_prompt,
    build_todo_prompt,
)

__all__ = ["build_ask_prompt", "build_summary_prompt", "build_todo_prompt"]
