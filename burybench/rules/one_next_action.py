"""Rule 3: End with one concrete next action."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import last_paragraph, prose

NEXT_DIRECTIVE_RE = re.compile(
    r"(?i)\b(?:next|then)\s*:\s*\S|\b(?:run|open|try|paste|check|verify|do)\b"
)

# Soft closers / open-ended invitations that are NOT a concrete next action
OPEN_ENDED_RE = re.compile(
    r"(?i)\b("
    r"let me know|"
    r"feel free|"
    r"happy to|"
    r"if you want|"
    r"if you'd like|"
    r"options? (?:include|are)|"
    r"you (?:could|can|might) (?:also )?(?:try|consider|look)|"
    r"several (?:ways|options|approaches)|"
    r"a few (?:options|ways|approaches)"
    r")\b"
)

OPTION_COUNT_RE = re.compile(
    r"(?i)\b(?:option|approach|alternative)\s*[A-C1-3]\b|"
    r"(?:^|\n)\s*[-*]\s+.+(?:\n\s*[-*]\s+.+){1,}",
)


class OneNextActionRule(Rule):
    name = "one_next_action"
    description = (
        "If anything is left open, name ONE concrete next action; "
        "closed-form answers are not applicable."
    )
    weight = 1.2

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        last = last_paragraph(prose(text))
        if not last:
            return RuleResult.not_applicable("empty response")

        if OPEN_ENDED_RE.search(last):
            # Offering multiple options / soft close without a single next step
            return RuleResult.failed(last[:160])

        # Multiple bullet options in the last paragraph => fail
        bullets = re.findall(r"(?m)^\s*[-*]\s+", last)
        if len(bullets) >= 2:
            return RuleResult.failed(last[:160])

        if NEXT_DIRECTIVE_RE.search(last):
            return RuleResult.passed()

        # Ends with a command-like last line or short closed answer
        if len(last.split()) <= 25 and not OPEN_ENDED_RE.search(last):
            return RuleResult.not_applicable("closed-form ending")

        return RuleResult.failed(last[:160])
