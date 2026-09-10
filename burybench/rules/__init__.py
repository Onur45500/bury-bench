"""Rule packs: adhd-v1 (single-turn) and adhd-v2 (+ multi-turn rules 5 and 7)."""

from __future__ import annotations

from burybench.rules.action_first import ActionFirstRule
from burybench.rules.base import Rule
from burybench.rules.capped_lists import CappedListsRule
from burybench.rules.error_tone import ErrorToneRule
from burybench.rules.no_closer import NoCloserRule
from burybench.rules.no_hedge_filler import NoHedgeFillerRule
from burybench.rules.no_idiom import NoIdiomRule
from burybench.rules.no_preamble import NoPreambleRule
from burybench.rules.no_tangent import NoTangentRule
from burybench.rules.numbered_steps import NumberedStepsRule
from burybench.rules.one_next_action import OneNextActionRule
from burybench.rules.restate_state import RestateStateRule
from burybench.rules.time_estimate import TimeEstimateRule
from burybench.rules.visible_wins import VisibleWinsRule

RULESET_V1 = "adhd-v1"
RULESET_V2 = "adhd-v2"
DEFAULT_RULESET = RULESET_V2


def v1_rules() -> list[Rule]:
    """Original V1 single-turn rule pack (comparable historical scores)."""
    return [
        ActionFirstRule(),
        NumberedStepsRule(),
        OneNextActionRule(),
        NoTangentRule(),
        TimeEstimateRule(),
        ErrorToneRule(),
        CappedListsRule(),
        NoPreambleRule(),
        NoCloserRule(),
        NoHedgeFillerRule(),
        NoIdiomRule(),
    ]


def v2_rules() -> list[Rule]:
    """V2 pack: V1 rules plus multi-turn restate_state and visible_wins."""
    return [
        *v1_rules(),
        RestateStateRule(),
        VisibleWinsRule(),
    ]


def rules_for(ruleset: str) -> list[Rule]:
    key = ruleset.strip().lower()
    if key in {RULESET_V1, "v1"}:
        return v1_rules()
    if key in {RULESET_V2, "v2", "default"}:
        return v2_rules()
    raise ValueError(f"Unknown ruleset {ruleset!r}. Choose: adhd-v1, adhd-v2.")


def default_rules() -> list[Rule]:
    """Default active pack (adhd-v2)."""
    return v2_rules()


__all__ = [
    "Rule",
    "RULESET_V1",
    "RULESET_V2",
    "DEFAULT_RULESET",
    "default_rules",
    "rules_for",
    "v1_rules",
    "v2_rules",
]
