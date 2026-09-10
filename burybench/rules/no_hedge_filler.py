"""Pre-send check 4: No hedging adverbs that add no information (density threshold)."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose, word_count

# Words/phrases that are typically filler hedges (not real uncertainty)
HEDGE_PATTERNS = [
    re.compile(r"(?i)\bperhaps\b"),
    re.compile(r"(?i)\bmight\b"),
    re.compile(r"(?i)\bcould possibly\b"),
    re.compile(r"(?i)\bmaybe\b"),
    re.compile(r"(?i)\bpossibly\b"),
    re.compile(r"(?i)\bit seems (?:like|that)?\b"),
    re.compile(r"(?i)\bit appears (?:that)?\b"),
    re.compile(r"(?i)\bin some (?:cases|sense)\b"),
    re.compile(r"(?i)\bsort of\b"),
    re.compile(r"(?i)\bkind of\b"),
    re.compile(r"(?i)\ba bit of a\b"),
]

# Default: fail if more than ~1 hedge word per 100 prose words
DEFAULT_THRESHOLD_PER_100 = 1.0


class NoHedgeFillerRule(Rule):
    name = "no_hedge_filler"
    description = (
        "Hedge-word density stays at or below ~1 per 100 prose words "
        "(proxy for 'keep hedges that carry real uncertainty')."
    )
    weight = 1.0

    def __init__(self, threshold_per_100: float = DEFAULT_THRESHOLD_PER_100) -> None:
        self.threshold_per_100 = threshold_per_100

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        body = prose(text)
        words = word_count(body)
        if words == 0:
            return RuleResult.not_applicable("empty prose")

        hits: list[str] = []
        for pattern in HEDGE_PATTERNS:
            for match in pattern.finditer(body):
                hits.append(match.group(0))

        if not hits:
            return RuleResult.passed()

        density = (len(hits) / words) * 100
        if density > self.threshold_per_100:
            return RuleResult.failed(
                f"{len(hits)} hedges / {words} words "
                f"({density:.1f}/100 > {self.threshold_per_100}): "
                + ", ".join(hits[:5])
            )
        return RuleResult.passed()
