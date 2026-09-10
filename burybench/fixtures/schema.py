"""Fixture schema — dataclass validation, no pydantic."""

from __future__ import annotations

from dataclasses import dataclass, field

from burybench.rules.base import Turn

VALID_CATEGORIES = frozenset({"debug", "install", "fix", "explain", "ambiguous"})
VALID_ROLES = frozenset({"user", "assistant"})


@dataclass(frozen=True)
class Fixture:
    id: str
    category: str
    prompt: str
    context: str | None = None
    notes: str | None = None
    turns: tuple[Turn, ...] = field(default_factory=tuple)

    @property
    def is_multi_turn(self) -> bool:
        return len(self.turns) > 0

    def transcript_turns(self) -> tuple[Turn, ...]:
        """Prior turns for scoring context (excludes the prompt being answered)."""
        return self.turns

    def full_prompt(self) -> str:
        """Prompt sent to the provider (last user content + optional context)."""
        if self.turns:
            # Include a readable transcript prefix so paste/API providers see history
            parts: list[str] = []
            for turn in self.turns:
                label = "User" if turn.role == "user" else "Assistant"
                parts.append(f"{label}:\n{turn.content.strip()}")
            parts.append(f"User:\n{self.prompt.strip()}")
            return "\n\n".join(parts)

        if self.context:
            return f"{self.context.rstrip()}\n\n{self.prompt.lstrip()}"
        return self.prompt


def _parse_turns(raw: object, *, source: str) -> tuple[Turn, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{source}: turns must be a list")
    turns: list[Turn] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{source}: turns[{i}] must be a mapping")
        role = str(item.get("role", "")).strip().lower()
        content = item.get("content")
        if role not in VALID_ROLES:
            raise ValueError(
                f"{source}: turns[{i}].role must be one of {sorted(VALID_ROLES)}"
            )
        if content is None or not str(content).strip():
            raise ValueError(f"{source}: turns[{i}].content must be non-empty")
        turns.append(Turn(role=role, content=str(content)))
    return tuple(turns)


def validate_fixture_dict(data: dict, *, source: str = "<unknown>") -> Fixture:
    """Validate a loaded YAML dict and return a Fixture. Raises ValueError on bad input."""
    if not isinstance(data, dict):
        raise ValueError(f"{source}: fixture root must be a mapping")

    required = ("id", "category", "prompt")
    missing = [k for k in required if k not in data or data[k] is None or data[k] == ""]
    if missing:
        raise ValueError(f"{source}: missing required fields: {', '.join(missing)}")

    fixture_id = str(data["id"]).strip()
    category = str(data["category"]).strip().lower()
    prompt = str(data["prompt"])

    if not fixture_id:
        raise ValueError(f"{source}: id must be non-empty")
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"{source}: category must be one of {sorted(VALID_CATEGORIES)}, got {category!r}"
        )
    if not prompt.strip():
        raise ValueError(f"{source}: prompt must be non-empty")

    context = data.get("context")
    notes = data.get("notes")
    turns = _parse_turns(data.get("turns"), source=source)

    return Fixture(
        id=fixture_id,
        category=category,
        prompt=prompt,
        context=str(context) if context is not None else None,
        notes=str(notes) if notes is not None else None,
        turns=turns,
    )
