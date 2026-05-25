from __future__ import annotations

import json
from typing import Any


def _find_session_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("session_id", "sessionId"):
            found = value.get(key)
            if isinstance(found, str) and found.strip():
                return found.strip()
        session = value.get("session")
        if isinstance(session, dict):
            found = session.get("id")
            if isinstance(found, str) and found.strip():
                return found.strip()
        for child in value.values():
            found = _find_session_id(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_session_id(child)
            if found:
                return found
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = []
        for item in value:
            text = _text_from_value(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip() or None
    if not isinstance(value, dict):
        return None

    for key in ("result", "output", "text", "content", "message"):
        if key not in value:
            continue
        candidate = value[key]
        if isinstance(candidate, dict) and key == "message":
            role = candidate.get("role")
            if role and role not in ("assistant", "agent"):
                continue
        text = _text_from_value(candidate)
        if text:
            return text

    parts = []
    for child in value.values():
        if isinstance(child, (dict, list)):
            text = _text_from_value(child)
            if text:
                parts.append(text)
    return "\n".join(parts).strip() or None


def _looks_like_cli_envelope(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    keys = set(record)
    return bool(
        keys
        & {
            "type",
            "subtype",
            "session_id",
            "stop_reason",
            "usage",
            "is_error",
            "api_error_status",
        }
    )


def extract_json_records(raw: str) -> list[Any]:
    decoder = json.JSONDecoder()
    records: list[Any] = []
    idx = 0
    while idx < len(raw):
        starts = [pos for pos in (raw.find("{", idx), raw.find("[", idx)) if pos >= 0]
        if not starts:
            break
        start = min(starts)
        try:
            record, end = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            idx = start + 1
            continue
        records.append(record)
        idx = end
    return records


def parse_agent_output(stdout: str) -> tuple[str, str | None]:
    raw = stdout.strip()
    if not raw:
        return "", None

    records = extract_json_records(raw)
    if not records:
        return raw, None

    session_id = None
    texts: list[str] = []
    for record in records:
        session_id = _find_session_id(record) or session_id
        text = _text_from_value(record)
        if text:
            texts.append(text)
    return ("\n".join(texts).strip() or raw), session_id


def sanitize_agent_body(body: str) -> str:
    raw = body.strip()
    if not raw:
        return body
    records = [record for record in extract_json_records(raw) if _looks_like_cli_envelope(record)]
    if not records:
        return body
    texts = [_text_from_value(record) for record in records]
    clean = "\n".join(text for text in texts if text).strip()
    return clean or body
