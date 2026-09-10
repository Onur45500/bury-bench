"""Rule 4: Suppress tangents."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

SIDEBAR_PATTERNS = [
    re.compile(r"(?i)\bby the way\b"),
    re.compile(r"(?i)\balso worth noting\b"),
    re.compile(r"(?i)\bwhile we['’]re at it\b"),
    re.compile(r"(?i)\bon a side note\b"),
    re.compile(r"(?i)\bas an aside\b"),
    re.compile(r"(?i)\bspeaking of which\b"),
    re.compile(r"(?i)\bin unrelated news\b"),
    re.compile(r"(?i)\bincidentally\b"),
]


class NoTangentRule(Rule):
    name = "no_tangent"
    description = "No mid-response sidebar markers (by the way, also worth noting, ...)."
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        body = prose(text)
        for pattern in SIDEBAR_PATTERNS:
            match = pattern.search(body)
            if match:
                return RuleResult.failed(match.group(0))
        return RuleResult.passed()
