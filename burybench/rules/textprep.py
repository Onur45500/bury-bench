"""Shared text preparation for rule checks.

Text rules run on prose only (code blocks / inline code stripped).
Structural rules run on raw markdown.
"""

from __future__ import annotations

import re

FENCED_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
# Match consecutive markdown list items (unordered or ordered)
LIST_ITEM_RE = re.compile(r"^(?:[ \t]*)(?:[-*+]|\d+[.)])[ \t]+(.+)$", re.MULTILINE)


def strip_code(text: str) -> str:
    """Remove fenced and inline code so code/error pastes never trigger text rules."""
    without_fenced = FENCED_CODE_RE.sub(" ", text)
    return INLINE_CODE_RE.sub(" ", without_fenced)


def prose(text: str) -> str:
    """Prose-only view of a response."""
    return strip_code(text)


def non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def first_line(text: str) -> str | None:
    lines = non_empty_lines(text)
    return lines[0] if lines else None


def last_line(text: str) -> str | None:
    lines = non_empty_lines(text)
    return lines[-1] if lines else None


def last_paragraph(text: str) -> str:
    """Return the last non-empty paragraph (split on blank lines)."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    return blocks[-1] if blocks else ""


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def extract_markdown_lists(text: str) -> list[list[str]]:
    """Extract flat consecutive list groups from markdown.

    Nested indentation does not start a new group; a blank line or non-list
    line closes the current group.
    """
    groups: list[list[str]] = []
    current: list[str] = []

    for line in text.splitlines():
        match = LIST_ITEM_RE.match(line)
        if match:
            current.append(match.group(1).strip())
        else:
            if current:
                groups.append(current)
                current = []
    if current:
        groups.append(current)
    return groups


def has_numbered_list(text: str) -> bool:
    return bool(re.search(r"^\s*\d+[.)]\s+\S", text, re.MULTILINE))
