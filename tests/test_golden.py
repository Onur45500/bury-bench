"""Golden regression tests."""

from __future__ import annotations

from pathlib import Path

from burybench.golden import evaluate_golden, load_golden_dir
from burybench.scorer import Scorer

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "golden"


def test_all_golden_cases_pass() -> None:
    cases = load_golden_dir(GOLDEN_ROOT)
    assert len(cases) >= 4
    failures: list[str] = []
    for case in cases:
        mismatches = evaluate_golden(case)
        if mismatches:
            failures.append(f"{case.id}: " + "; ".join(mismatches))
    assert not failures, "\n".join(failures)


def test_golden_catches_deliberate_regression() -> None:
    """If no_preamble is broken to always pass, golden-buried-preamble fails."""
    from burybench.rules.base import RuleResult, ScoreContext
    from burybench.rules.no_preamble import NoPreambleRule
    from burybench.rules import rules_for

    class BrokenPreamble(NoPreambleRule):
        def _check(self, context: ScoreContext) -> RuleResult:
            return RuleResult.passed()

    rules = []
    for rule in rules_for("adhd-v2"):
        if rule.name == "no_preamble":
            rules.append(BrokenPreamble())
        else:
            rules.append(rule)

    cases = {c.id: c for c in load_golden_dir(GOLDEN_ROOT)}
    buried = cases["golden-buried-preamble"]
    scorer = Scorer(rules=rules, ruleset="adhd-v2")
    mismatches = evaluate_golden(buried, scorer=scorer)
    assert any("no_preamble" in m for m in mismatches)
