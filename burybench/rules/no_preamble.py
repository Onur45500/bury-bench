"""Rule 10a: No preamble / forbidden openers."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import first_line

# Forbidden openers from SKILL.md rule 10, plus close variants
OPENER_PATTERNS = [
    re.compile(r"(?i)^great question\b"),
    re.compile(r"(?i)^let me\b"),
    re.compile(r"(?i)^i['’]ll\b"),
    re.compile(r"(?i)^sure[!.,]?\s"),
    re.compile(r"(?i)^sure!$"),
    re.compile(r"(?i)^looking at (?:your|the)\b"),
    re.compile(r"(?i)^to answer your question\b"),
    re.compile(r"(?i)^absolutely[!.,]?\b"),
    re.compile(r"(?i)^of course[!.,]?\b"),
    re.compile(r"(?i)^thanks for (?:asking|sharing|the)\b"),
    re.compile(r"(?i)^i('d| would) be happy to\b"),
    re.compile(r"(?i)^happy to help\b"),
    re.compile(r"(?i)^let's (?:think|dive|take a look|explore)\b"),
]


class NoPreambleRule(Rule):
    name = "no_preamble"
    description = (
        "No forbidden openers: 'Great question', 'Let me...', 'I'll...', "
        "'Sure!', 'Looking at your...', 'To answer your question...'"
    )
    weight = 1.5

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        line = first_line(text)
        if line is None:
            return RuleResult.not_applicable("empty response")

        for pattern in OPENER_PATTERNS:
            match = pattern.search(line)
            if match:
                return RuleResult.failed(match.group(0).strip())
        return RuleResult.passed()
