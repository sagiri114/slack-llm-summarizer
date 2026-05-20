#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Please edit it before running the bot."
else
  echo ".env already exists."
fi

pip install -e ".[dev]"
echo "Done. Next: edit .env, then run: make run"
