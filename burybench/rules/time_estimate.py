"""Rule 6: Give specific time estimates."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

# Language that indicates an estimate is being attempted
ESTIMATE_SIGNAL_RE = re.compile(
    r"(?i)\b("
    r"will take|takes about|takes roughly|should take|estimate|"
    r"about \d+|roughly \d+|around \d+|"
    r"some work|a (?:bit|little) of (?:work|time)|a while|"
    r"shortly|soon|quickly|a few (?:minutes|hours|days)|"
    r"an? (?:hour|minute|day|afternoon|morning|evening)|"
    r"\d+\s*(?:min(?:ute)?s?|hours?|days?)"
    r")\b"
)

VAGUE_ESTIMATE_RE = re.compile(
    r"(?i)\b("
    r"some work|"
    r"a (?:bit|little) of (?:work|time)|"
    r"a while|"
    r"shortly|"
    r"soon|"
    r"quickly|"
    r"not (?:too )?long|"
    r"a moment|"
    r"a sec(?:ond)?|"
    r"real quick|"
    r"pretty quick"
    r")\b"
)

CONCRETE_UNIT_RE = re.compile(
    r"(?i)\b("
    r"\d+\s*(?:min(?:ute)?s?|hours?|days?|weeks?)|"
    r"an? (?:hour|minute|day|afternoon|morning|evening)|"
    r"half (?:an? )?hour|"
    r"a few (?:minutes|hours|days)"
    r")\b"
)


class TimeEstimateRule(Rule):
    name = "time_estimate"
    description = (
        "When an estimate is given, use concrete units; "
        "vague estimates fail. N/A if no estimate language present."
    )
    weight = 0.8

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        body = prose(text)
        if not ESTIMATE_SIGNAL_RE.search(body):
            return RuleResult.not_applicable("no estimate language")

        vague = VAGUE_ESTIMATE_RE.search(body)
        concrete = CONCRETE_UNIT_RE.search(body)

        if vague and not concrete:
            return RuleResult.failed(vague.group(0))

        if concrete:
            return RuleResult.passed()

        # Estimate signal without concrete unit and without known vague phrase
        return RuleResult.failed("estimate without concrete unit")
