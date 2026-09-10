"""Pre-send check 4: No hedging adverbs that add no information.

Hybrid proxy (still deterministic):
- density threshold (~1 hedge / 100 prose words), OR
- opening-window cluster (2+ hedges before the first code fence / in the
  first ~2 sentences), OR
- absolute opening spam (3+ hedges in the opening window)

Short replies with a single hedge are allowed (honest uncertainty).
Hedges inside diagnostic templates are not counted.
"""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose, word_count

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

# Honest diagnostic framing — hedges here do not count
DIAGNOSTIC_SENTENCE_RE = re.compile(
    r"(?i)\b("
    r"if (?:that|this|it) fails|"
    r"unknown until|"
    r"paste the|"
    r"once we (?:see|have)|"
    r"depending on whether|"
    r"need (?:the|a) (?:log|trace|repro)|"
    r"cannot tell (?:yet|until)"
    r")\b"
)

DEFAULT_THRESHOLD_PER_100 = 1.0
DEFAULT_OPENING_CLUSTER = 2
DEFAULT_OPENING_SPAM = 3
DEFAULT_SHORT_WORDS = 80


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _opening_window(body: str) -> str:
    """Prose before the first fenced block cue, limited to first two sentences."""
    before_fence = re.split(r"```", body, maxsplit=1)[0]
    sents = _sentences(before_fence)
    if not sents:
        return before_fence.strip()
    return " ".join(sents[:2])


def _find_hedges(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in HEDGE_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(match.group(0))
    return hits


def _countable_hedges(text: str) -> list[str]:
    """Hedges excluding those inside diagnostic sentences."""
    sents = _sentences(text)
    if not sents:
        if text.strip() and not DIAGNOSTIC_SENTENCE_RE.search(text):
            return _find_hedges(text)
        return []
    counted: list[str] = []
    for sentence in sents:
        if DIAGNOSTIC_SENTENCE_RE.search(sentence):
            continue
        counted.extend(_find_hedges(sentence))
    return counted


class NoHedgeFillerRule(Rule):
    name = "no_hedge_filler"
    description = (
        "Hedge proxy: density <= ~1/100 words, and no opening hedge cluster "
        "(2+ in first sentences). Single short honest hedge allowed."
    )
    weight = 1.0

    def __init__(
        self,
        threshold_per_100: float = DEFAULT_THRESHOLD_PER_100,
        opening_cluster: int = DEFAULT_OPENING_CLUSTER,
        opening_spam: int = DEFAULT_OPENING_SPAM,
        short_words: int = DEFAULT_SHORT_WORDS,
    ) -> None:
        self.threshold_per_100 = threshold_per_100
        self.opening_cluster = opening_cluster
        self.opening_spam = opening_spam
        self.short_words = short_words

    def _check(self, context: ScoreContext) -> RuleResult:
        body = prose(context.response)
        words = word_count(body)
        if words == 0:
            return RuleResult.not_applicable("empty prose")

        hits = _countable_hedges(body)
        if not hits:
            return RuleResult.passed()

        # One hedge in a short reply = honest uncertainty, not filler spam
        if len(hits) == 1 and words <= self.short_words:
            return RuleResult.passed()

        opening = _opening_window(body)
        opening_hits = _countable_hedges(opening)

        if len(opening_hits) >= self.opening_spam:
            return RuleResult.failed(
                f"opening hedge spam ({len(opening_hits)}): "
                + ", ".join(opening_hits[:5])
            )

        if len(opening_hits) >= self.opening_cluster:
            return RuleResult.failed(
                f"opening hedge cluster ({len(opening_hits)}): "
                + ", ".join(opening_hits[:5])
            )

        density = (len(hits) / words) * 100
        if density > self.threshold_per_100:
            return RuleResult.failed(
                f"{len(hits)} hedges / {words} words "
                f"({density:.1f}/100 > {self.threshold_per_100}): "
                + ", ".join(hits[:5])
            )
        return RuleResult.passed()
