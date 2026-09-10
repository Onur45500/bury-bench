"""Golden regression cases: hand-scored responses with expected rule statuses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from burybench.rules.base import RuleStatus, Turn
from burybench.scorer import Scorer


@dataclass(frozen=True)
class GoldenCase:
    id: str
    response: str
    expected: dict[str, str]  # rule name -> passed|failed|not_applicable
    turns: tuple[Turn, ...] = ()
    ruleset: str = "adhd-v2"
    notes: str | None = None


def load_golden_case(path: Path | str) -> GoldenCase:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: golden root must be a mapping")
    for key in ("id", "response", "expected"):
        if key not in data:
            raise ValueError(f"{path}: missing {key}")
    turns_raw = data.get("turns") or []
    turns = tuple(
        Turn(role=str(t["role"]).lower(), content=str(t["content"])) for t in turns_raw
    )
    expected = {str(k): str(v) for k, v in data["expected"].items()}
    return GoldenCase(
        id=str(data["id"]),
        response=str(data["response"]),
        expected=expected,
        turns=turns,
        ruleset=str(data.get("ruleset", "adhd-v2")),
        notes=str(data["notes"]) if data.get("notes") is not None else None,
    )


def load_golden_dir(path: Path | str) -> list[GoldenCase]:
    root = Path(path)
    files = sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml"))
    return [load_golden_case(f) for f in files]


def evaluate_golden(case: GoldenCase, scorer: Scorer | None = None) -> list[str]:
    """Return list of mismatch descriptions (empty = pass)."""
    scorer = scorer or Scorer.from_ruleset(case.ruleset)
    result = scorer.score(case.response, turns=case.turns)
    by_name = {r.name: r.status for r in result.rules}
    mismatches: list[str] = []
    for rule_name, expected_status in case.expected.items():
        actual = by_name.get(rule_name)
        if actual is None:
            mismatches.append(f"{rule_name}: missing from scorer (expected {expected_status})")
        elif actual != expected_status:
            mismatches.append(f"{rule_name}: expected {expected_status}, got {actual}")
    return mismatches
