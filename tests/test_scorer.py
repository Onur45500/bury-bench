"""Scorer aggregation tests."""

from __future__ import annotations

from burybench.rules.base import Rule, RuleResult, RuleStatus, ScoreContext, Turn
from burybench.rules import RULESET_V1, RULESET_V2, rules_for
from burybench.scorer import Scorer


class AlwaysPass(Rule):
    name = "always_pass"
    description = "always passes"
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        return RuleResult.passed()


class AlwaysFail(Rule):
    name = "always_fail"
    description = "always fails"
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        return RuleResult.failed("nope")


class AlwaysNA(Rule):
    name = "always_na"
    description = "always n/a"
    weight = 5.0

    def _check(self, context: ScoreContext) -> RuleResult:
        return RuleResult.not_applicable("skip")


class HeavyFail(Rule):
    name = "heavy_fail"
    description = "weighted fail"
    weight = 3.0

    def _check(self, context: ScoreContext) -> RuleResult:
        return RuleResult.failed("heavy")


def test_perfect_score() -> None:
    result = Scorer(rules=[AlwaysPass(), AlwaysPass()]).score("anything")
    assert result.score == 100.0
    assert result.applicable_weight == 2.0
    assert result.passed_weight == 2.0


def test_zero_score() -> None:
    result = Scorer(rules=[AlwaysFail()]).score("x")
    assert result.score == 0.0


def test_all_na_is_100() -> None:
    result = Scorer(rules=[AlwaysNA(), AlwaysNA()]).score("x")
    assert result.score == 100.0
    assert result.applicable_weight == 0.0


def test_weighted_mix() -> None:
    # pass 1.0, fail 3.0 => 25
    result = Scorer(rules=[AlwaysPass(), HeavyFail()]).score("x")
    assert result.score == 25.0
    assert result.passed_weight == 1.0
    assert result.applicable_weight == 4.0


def test_na_excluded_from_denominator() -> None:
    result = Scorer(rules=[AlwaysPass(), AlwaysNA(), AlwaysFail()]).score("x")
    assert result.score == 50.0
    assert result.applicable_weight == 2.0


def test_breakdown_includes_all_rules() -> None:
    result = Scorer(rules=[AlwaysPass(), AlwaysFail(), AlwaysNA()]).score("hi")
    names = [r.name for r in result.rules]
    assert names == ["always_pass", "always_fail", "always_na"]
    assert result.rules[1].evidence == "nope"
    assert result.rules[2].status == RuleStatus.NOT_APPLICABLE.value


def test_reproducible() -> None:
    from burybench.rules import default_rules

    text = (
        "Great question! Let me think about this.\n\n"
        "First do X then do Y after that do Z.\n\n"
        "Hope this helps!"
    )
    a = Scorer(rules=default_rules()).score(text)
    b = Scorer(rules=default_rules()).score(text)
    assert a.score == b.score
    assert [r.status for r in a.rules] == [r.status for r in b.rules]


def test_default_rules_score_good_response() -> None:
    text = (
        "Run `pip install fastapi`.\n\n"
        "1. Add the import\n"
        "2. Create the app\n"
        "3. Run `uvicorn main:app`\n\n"
        "Next: open http://127.0.0.1:8000/docs."
    )
    result = Scorer().score(text)
    assert result.score >= 80.0


def test_default_rules_score_buried_response() -> None:
    text = (
        "Great question! Let me walk you through this carefully.\n\n"
        "First you should maybe look at the logs, then perhaps restart, "
        "after that you might circle back to the config.\n\n"
        "By the way, your README is also stale.\n\n"
        "Hope this helps! Let me know if you need anything else."
    )
    result = Scorer().score(text)
    assert result.score < 50.0


def test_v1_ruleset_excludes_multiturn_rules() -> None:
    names = {r.name for r in rules_for(RULESET_V1)}
    assert "restate_state" not in names
    assert "visible_wins" not in names
    assert "action_first" in names


def test_v2_ruleset_includes_multiturn_rules() -> None:
    names = {r.name for r in rules_for(RULESET_V2)}
    assert "restate_state" in names
    assert "visible_wins" in names


def test_v1_score_unchanged_on_single_turn() -> None:
    text = (
        "Run `pip install fastapi`.\n\n"
        "1. Add the import\n"
        "2. Create the app\n"
        "3. Run `uvicorn main:app`\n\n"
        "Next: open http://127.0.0.1:8000/docs."
    )
    v1 = Scorer.from_ruleset(RULESET_V1).score(text)
    v2 = Scorer.from_ruleset(RULESET_V2).score(text)
    # Multi-turn rules are N/A on single-turn, so scores match
    assert v1.score == v2.score


def test_multiturn_scoring_uses_prior_assistant() -> None:
    prior = "Step 2 of 5 done: schema updated. Next: backfill the column."
    good = "Step 2 of 5 done: schema updated. Next: run `python backfill.py`."
    turns = (Turn(role="assistant", content=prior),)
    result = Scorer.from_ruleset(RULESET_V2).score(good, turns=turns)
    statuses = {r.name: r.status for r in result.rules}
    assert statuses["restate_state"] == RuleStatus.PASSED.value
