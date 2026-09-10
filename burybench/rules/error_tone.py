"""Rule 8: Matter-of-fact tone for errors."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

ERROR_TONE_PATTERNS = [
    re.compile(r"(?i)\buh[\s-]?oh\b"),
    re.compile(r"(?i)\boh[\s-]?no\b"),
    re.compile(r"(?i)\bthere seems to be (?:a |an )?(?:problem|issue|error)\b"),
    re.compile(r"(?i)\bit (?:looks|seems) like (?:there(?:'s| is) )?(?:a |an )?(?:problem|issue)\b"),
    re.compile(r"(?i)\bwhoops\b"),
    re.compile(r"(?i)\byikes\b"),
]


class ErrorToneRule(Rule):
    name = "error_tone"
    description = (
        "Never use 'Uh oh', 'Oh no', or 'There seems to be a problem'. "
        "State cause and fix."
    )
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        body = prose(text)
        for pattern in ERROR_TONE_PATTERNS:
            match = pattern.search(body)
            if match:
                return RuleResult.failed(match.group(0))
        return RuleResult.passed()
