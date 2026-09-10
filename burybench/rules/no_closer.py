"""Rule 10b: No closing pleasantries."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import last_line, prose

CLOSER_PATTERNS = [
    re.compile(r"(?i)\blet me know if (?:you need|you have|there's|there is|anything)\b"),
    re.compile(r"(?i)\bhope (?:this|that) helps\b"),
    re.compile(r"(?i)\bhappy to clarify\b"),
    re.compile(r"(?i)\bfeel free to (?:ask|reach out|let me know)\b"),
    re.compile(r"(?i)\bdon['’]t hesitate to (?:ask|reach out)\b"),
    re.compile(r"(?i)\blet me know if you (?:need|want) anything else\b"),
    re.compile(r"(?i)\bhappy to help (?:further|with anything else)\b"),
    re.compile(r"(?i)\bgood luck[!.,]?\s*$"),
]


class NoCloserRule(Rule):
    name = "no_closer"
    description = (
        "No forbidden closers: 'Hope this helps', 'Let me know if...', "
        "'Happy to clarify', 'Feel free to ask'."
    )
    weight = 1.2

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        # Check last few non-empty lines — closers often sit on their own line
        lines = [ln.strip() for ln in prose(text).splitlines() if ln.strip()]
        if not lines:
            return RuleResult.not_applicable("empty response")

        tail = "\n".join(lines[-3:])
        for pattern in CLOSER_PATTERNS:
            match = pattern.search(tail)
            if match:
                return RuleResult.failed(match.group(0))

        # Also check last line alone for short closers
        last = last_line(prose(text))
        if last:
            for pattern in CLOSER_PATTERNS:
                match = pattern.search(last)
                if match:
                    return RuleResult.failed(match.group(0))

        return RuleResult.passed()
