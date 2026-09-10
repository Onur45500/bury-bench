"""Provider adapter unit tests (no live API calls)."""

from __future__ import annotations

import pytest

from burybench.providers import get_provider


def test_get_paste_provider() -> None:
    p = get_provider("paste")
    assert p.name == "paste"


def test_openai_requires_model() -> None:
    with pytest.raises(ValueError, match="model"):
        get_provider("openai")


def test_openai_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
        get_provider("openai", model="gpt-4o-mini")


def test_anthropic_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic", model="claude-sonnet-4-20250514")


def test_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nope")
