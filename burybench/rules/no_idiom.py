"""Pre-send check 5: No idioms or figurative phrases."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

IDIOM_PATTERNS = [
    re.compile(r"(?i)\bcircle back\b"),
    re.compile(r"(?i)\bget the ball rolling\b"),
    re.compile(r"(?i)\bon the same page\b"),
    re.compile(r"(?i)\blow[- ]hanging fruit\b"),
    re.compile(r"(?i)\bmove the needle\b"),
    re.compile(r"(?i)\btake it offline\b"),
    re.compile(r"(?i)\bdrill down\b"),
    re.compile(r"(?i)\bthink outside the box\b"),
    re.compile(r"(?i)\bhit the ground running\b"),
    re.compile(r"(?i)\bboil the ocean\b"),
    re.compile(r"(?i)\bpeel (?:back )?the onion\b"),
    re.compile(r"(?i)\bopen (?:up )?a can of worms\b"),
    re.compile(r"(?i)\bgo (?:the )?extra mile\b"),
    re.compile(r"(?i)\bat the end of the day\b"),
    re.compile(r"(?i)\bsilver bullet\b"),
    re.compile(r"(?i)\bband[- ]?aid (?:fix|solution)\b"),
    re.compile(r"(?i)\bquick[- ]?and[- ]?dirty\b"),
]


class NoIdiomRule(Rule):
    name = "no_idiom"
    description = (
        "No idioms or figurative phrases "
        "('circle back', 'get the ball rolling', 'on the same page', ...)."
    )
    weight = 0.8

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        body = prose(text)
        for pattern in IDIOM_PATTERNS:
            match = pattern.search(body)
            if match:
                return RuleResult.failed(match.group(0))
        return RuleResult.passed()
