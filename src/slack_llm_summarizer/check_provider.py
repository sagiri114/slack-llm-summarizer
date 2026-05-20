from __future__ import annotations

import asyncio
import sys

from slack_llm_summarizer.config import Settings
from slack_llm_summarizer.errors import ConfigurationError
from slack_llm_summarizer.providers import build_provider
from slack_llm_summarizer.startup import validate_llm_settings


async def _run_check(settings: Settings, provider_name: str | None = None) -> int:
    provider = provider_name or settings.llm_provider
    print(f"LLM_PROVIDER (active): {provider}")

    try:
        validate_llm_settings(settings, provider)
    except ConfigurationError as exc:
        print(f"Configuration: FAILED")
        print(f"Reason: {exc.user_message}")
        return 1

    cfg = settings.provider_settings(provider)  # type: ignore[arg-type]
    print(f"Model: {cfg.model}")
    print(f"Base URL: {cfg.base_url or '(gemini default)'}")
    print(f"Temperature: {settings.llm_temperature}")
    print(f"Max tokens: {settings.llm_max_tokens}")
    print("API key: configured")

    system = "You are a helpful assistant."
    user = 'Reply with JSON only: {"status":"ok","message":"provider check"}'

    try:
        llm = build_provider(settings, provider)
        data = await llm.complete_json(system, user)
    except ConfigurationError as exc:
        print("LLM call: FAILED")
        print(f"Reason: {exc.user_message}")
        return 1
    except Exception as exc:
        print("LLM call: FAILED")
        print(f"Reason: {type(exc).__name__}: {exc}")
        print("Hints: 检查 API Key、余额、base_url、模型名是否正确。")
        return 1

    print("LLM call: OK")
    print(f"Sample response keys: {list(data.keys())}")
    return 0


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    provider_override = args[0] if args else None

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Configuration: FAILED\nReason: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Default LLM_PROVIDER from .env: {settings.llm_provider}")
    code = asyncio.run(_run_check(settings, provider_override))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
