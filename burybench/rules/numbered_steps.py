"""Rule 2: Number multi-step tasks."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import has_numbered_list, prose

SEQUENCE_MARKERS = [
    re.compile(r"\bfirst\b[,:]?", re.IGNORECASE),
    re.compile(r"\bthen\b", re.IGNORECASE),
    re.compile(r"\bafter that\b", re.IGNORECASE),
    re.compile(r"\bnext[,:]\s", re.IGNORECASE),
    re.compile(r"\bfinally\b", re.IGNORECASE),
    re.compile(r"\bafterwards\b", re.IGNORECASE),
    re.compile(r"\bsubsequently\b", re.IGNORECASE),
]


class NumberedStepsRule(Rule):
    name = "numbered_steps"
    description = (
        "Multi-step work uses a numbered list; prose sequence markers "
        "without a numbered list fail."
    )
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        if has_numbered_list(text):
            return RuleResult.passed()

        body = prose(text)
        hits: list[str] = []
        for pattern in SEQUENCE_MARKERS:
            match = pattern.search(body)
            if match:
                hits.append(match.group(0))

        if len(hits) >= 2:
            return RuleResult.failed(", ".join(hits[:4]))

        return RuleResult.not_applicable("no multi-step sequence detected")
