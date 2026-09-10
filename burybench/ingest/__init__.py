"""Ingest agent transcripts into scoreable response payloads."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from burybench.rules.base import Turn

ROLE_ALIASES = {
    "user": "user",
    "human": "user",
    "assistant": "assistant",
    "ai": "assistant",
    "model": "assistant",
    "bot": "assistant",
}


@dataclass
class IngestedTranscript:
    id: str
    category: str
    response_text: str
    turns: list[dict]
    source: str

    def to_score_item(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "response_text": self.response_text,
            "turns": self.turns,
        }


def _norm_role(role: str) -> str:
    key = role.strip().lower()
    if key not in ROLE_ALIASES:
        raise ValueError(f"Unknown role {role!r}")
    return ROLE_ALIASES[key]


def _turns_from_dicts(items: list[dict]) -> list[Turn]:
    turns: list[Turn] = []
    for i, item in enumerate(items):
        role = _norm_role(str(item.get("role", "")))
        content = item.get("content")
        if content is None:
            content = item.get("text")
        if content is None or not str(content).strip():
            raise ValueError(f"turn[{i}] missing content")
        turns.append(Turn(role=role, content=str(content)))
    return turns


def parse_jsonl(path: Path | str, *, default_category: str = "debug") -> list[IngestedTranscript]:
    """Each line is a JSON object with messages/turns and optional id/category.

    The last assistant message is the response under test; earlier messages
    become prior turns.
    """
    path = Path(path)
    out: list[IngestedTranscript] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON") from exc
        out.append(_from_message_obj(obj, default_category=default_category, source=f"{path}:{lineno}"))
    return out


def parse_cursor_export(path: Path | str, *, default_category: str = "debug") -> list[IngestedTranscript]:
    """Parse a Cursor-like JSON export: {conversations:[{id, messages:[{role,content}]}]} or a bare messages list."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    conversations: list[dict]
    if isinstance(data, list):
        conversations = [{"id": f"cursor-{i}", "messages": item if isinstance(item, list) else item.get("messages", [])} for i, item in enumerate(data)]
        # normalize
        fixed = []
        for i, item in enumerate(data):
            if isinstance(item, list):
                fixed.append({"id": f"cursor-{i}", "messages": item})
            elif isinstance(item, dict):
                fixed.append(item)
            else:
                raise ValueError(f"Unsupported cursor export item type at index {i}")
        conversations = fixed
    elif isinstance(data, dict) and "conversations" in data:
        conversations = list(data["conversations"])
    elif isinstance(data, dict) and ("messages" in data or "turns" in data):
        conversations = [data]
    else:
        raise ValueError("Unsupported cursor-export shape")

    results: list[IngestedTranscript] = []
    for i, conv in enumerate(conversations):
        msgs = conv.get("messages") or conv.get("turns") or []
        obj = {
            "id": conv.get("id") or f"cursor-{i}",
            "category": conv.get("category", default_category),
            "messages": msgs,
        }
        results.append(
            _from_message_obj(obj, default_category=default_category, source=f"{path}#{i}")
        )
    return results


_MD_TURN_RE = re.compile(
    r"(?im)^(#{1,3}\s*)?(user|human|assistant|ai|model)\s*:?\s*$"
)


def parse_markdown(path: Path | str, *, default_category: str = "debug") -> list[IngestedTranscript]:
    """Parse a markdown transcript with User:/Assistant: (or ## User) headings."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    turns: list[dict] = []
    current_role: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current_role, buf
        if current_role is not None:
            content = "\n".join(buf).strip()
            if content:
                turns.append({"role": current_role, "content": content})
        buf = []

    for line in lines:
        match = _MD_TURN_RE.match(line.strip())
        if match:
            flush()
            current_role = _norm_role(match.group(2))
            continue
        if current_role is not None:
            buf.append(line)
    flush()

    if not turns:
        raise ValueError(f"{path}: no User:/Assistant: turns found")

    obj = {"id": path.stem, "category": default_category, "messages": turns}
    return [_from_message_obj(obj, default_category=default_category, source=str(path))]


def _from_message_obj(
    obj: dict,
    *,
    default_category: str,
    source: str,
) -> IngestedTranscript:
    msgs = obj.get("messages") or obj.get("turns") or obj.get("conversation")
    if not isinstance(msgs, list) or not msgs:
        raise ValueError(f"{source}: expected non-empty messages/turns list")

    turns = _turns_from_dicts(msgs)
    # Last assistant message is the response under test
    last_assistant_idx = None
    for i in range(len(turns) - 1, -1, -1):
        if turns[i].role == "assistant":
            last_assistant_idx = i
            break
    if last_assistant_idx is None:
        raise ValueError(f"{source}: no assistant message to score")

    response = turns[last_assistant_idx].content
    prior = turns[:last_assistant_idx]
    transcript_id = str(obj.get("id") or Path(source).stem)
    category = str(obj.get("category") or default_category)
    return IngestedTranscript(
        id=transcript_id,
        category=category,
        response_text=response,
        turns=[{"role": t.role, "content": t.content} for t in prior],
        source=source,
    )


def ingest(
    path: Path | str,
    *,
    fmt: str,
    default_category: str = "debug",
) -> list[IngestedTranscript]:
    key = fmt.strip().lower()
    if key in {"jsonl", "ndjson"}:
        return parse_jsonl(path, default_category=default_category)
    if key in {"cursor", "cursor-export", "cursor_export"}:
        return parse_cursor_export(path, default_category=default_category)
    if key in {"markdown", "md"}:
        return parse_markdown(path, default_category=default_category)
    raise ValueError(f"Unknown ingest format {fmt!r}. Choose: jsonl, cursor-export, markdown.")
