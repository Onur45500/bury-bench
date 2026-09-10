"""Aggregate rule results into a 0–100 action score."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from burybench.rules import DEFAULT_RULESET, default_rules, rules_for
from burybench.rules.base import Rule, RuleResult, RuleStatus, ScoreContext, Turn


@dataclass(frozen=True)
class RuleBreakdown:
    name: str
    status: str
    evidence: str | None
    weight: float


@dataclass(frozen=True)
class ScoreResult:
    """Action score for a single response: higher = better."""

    score: float
    rules: list[RuleBreakdown]
    passed_weight: float
    applicable_weight: float
    ruleset: str = DEFAULT_RULESET

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed_weight": self.passed_weight,
            "applicable_weight": self.applicable_weight,
            "ruleset": self.ruleset,
            "rules": [asdict(r) for r in self.rules],
        }


@dataclass
class Scorer:
    rules: list[Rule] = field(default_factory=default_rules)
    ruleset: str = DEFAULT_RULESET

    @classmethod
    def from_ruleset(cls, ruleset: str) -> Scorer:
        return cls(rules=rules_for(ruleset), ruleset=ruleset)

    def score(
        self,
        text: str,
        *,
        turns: list[Turn] | tuple[Turn, ...] | None = None,
    ) -> ScoreResult:
        ctx = ScoreContext(response=text, turns=tuple(turns or ()))
        breakdown: list[RuleBreakdown] = []
        passed_weight = 0.0
        applicable_weight = 0.0

        for rule in self.rules:
            result: RuleResult = rule.check(text, context=ctx)
            breakdown.append(
                RuleBreakdown(
                    name=rule.name,
                    status=result.status.value,
                    evidence=result.evidence,
                    weight=rule.weight,
                )
            )
            if result.status is RuleStatus.NOT_APPLICABLE:
                continue
            applicable_weight += rule.weight
            if result.status is RuleStatus.PASSED:
                passed_weight += rule.weight

        if applicable_weight == 0:
            score = 100.0
        else:
            score = round(100.0 * passed_weight / applicable_weight, 2)

        return ScoreResult(
            score=score,
            rules=breakdown,
            passed_weight=passed_weight,
            applicable_weight=applicable_weight,
            ruleset=self.ruleset,
        )
