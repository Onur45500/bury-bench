"""Validate every fixture YAML against the schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from burybench.fixtures import load_fixture, load_fixtures
from burybench.fixtures.schema import VALID_CATEGORIES

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_all_fixtures_valid() -> None:
    fixtures = load_fixtures(FIXTURES_ROOT)
    assert len(fixtures) >= 30
    ids = {fx.id for fx in fixtures}
    assert len(ids) == len(fixtures)


def test_categories_covered() -> None:
    fixtures = load_fixtures(FIXTURES_ROOT)
    cats = {fx.category for fx in fixtures}
    # Core V1 categories must remain; V2 adds explain + ambiguous.
    assert {"debug", "install", "fix"}.issubset(cats)
    assert cats <= VALID_CATEGORIES
    for cat in cats:
        assert sum(1 for fx in fixtures if fx.category == cat) >= 8


def test_fixture_count_v2() -> None:
    fixtures = load_fixtures(FIXTURES_ROOT)
    # Exclude golden expected-outcome files from the prompt corpus count
    prompt_fixtures = [fx for fx in fixtures if not fx.id.startswith("golden-")]
    assert len(prompt_fixtures) >= 80


def test_multiturn_fixture_parses(tmp_path: Path) -> None:
    path = tmp_path / "mt.yaml"
    path.write_text(
        """
id: debug-mt-test
category: debug
turns:
  - role: user
    content: start the migration
  - role: assistant
    content: |
      Step 1 of 3 done: schema updated.
prompt: |
  continue
notes: >
  multi-turn smoke
""",
        encoding="utf-8",
    )
    fx = load_fixture(path)
    assert fx.is_multi_turn
    assert len(fx.turns) == 2
    assert "Assistant:" in fx.full_prompt()


def test_each_file_has_required_fields() -> None:
    for path in sorted(FIXTURES_ROOT.rglob("*.yaml")):
        fx = load_fixture(path)
        assert fx.id
        assert fx.prompt.strip()
        assert fx.category in VALID_CATEGORIES


def test_fixture_ids_match_filenames() -> None:
    for path in sorted(FIXTURES_ROOT.rglob("*.yaml")):
        fx = load_fixture(path)
        assert path.stem == fx.id


def test_full_prompt_includes_context() -> None:
    fx = load_fixture(FIXTURES_ROOT / "debug" / "debug-007.yaml")
    assert fx.context
    assert fx.context in fx.full_prompt()
    assert fx.prompt.strip() in fx.full_prompt()


def test_invalid_category_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "id: bad-001\ncategory: weird\nprompt: |\n  hello\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="category"):
        load_fixture(bad)


def test_missing_prompt_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("id: bad-002\ncategory: debug\nprompt: |\n  \n", encoding="utf-8")
    with pytest.raises(ValueError, match="prompt"):
        load_fixture(bad)
