from __future__ import annotations

import json
import re

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_json_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return text
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text


def parse_json_dict(raw: str) -> dict:
    text = extract_json_text(raw)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("LLM response JSON must be an object")
    return data
