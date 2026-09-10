"""Rule 9: Cap lists to 5 items."""

from __future__ import annotations

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import extract_markdown_lists


class CappedListsRule(Rule):
    name = "capped_lists"
    description = "No markdown list group exceeds 5 visible items."
    weight = 1.0

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        groups = extract_markdown_lists(text)
        if not groups:
            return RuleResult.not_applicable("no markdown lists")

        for group in groups:
            if len(group) > 5:
                preview = "; ".join(group[:3]) + f" ... (+{len(group) - 3} more)"
                return RuleResult.failed(f"{len(group)} items: {preview}")
        return RuleResult.passed()
