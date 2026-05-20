.PHONY: install setup run test check dry-run

install:
	pip install -e ".[dev]"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; else echo ".env already exists"; fi

run:
	slack-llm-summarizer

test:
	pytest -q

check:
	python -m slack_llm_summarizer.check_provider

dry-run:
	slack-summary-dry-run --input samples/messages.json
