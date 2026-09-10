"""Rule 7: Make completed work visible (multi-turn only)."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import first_line, prose

COMPLETION_CLAIM_RE = re.compile(
    r"(?i)\b("
    r"i('ve| have) (?:now )?(?:done|fixed|updated|added|changed|implemented)|"
    r"(?:done|fixed|updated|added|patched|completed)\b|"
    r"changes? (?:are|were) (?:made|applied)|"
    r"among other things"
    r")"
)

BURIED_RECAP_RE = re.compile(
    r"(?i)\b("
    r"i('ve| have) made some changes|"
    r"among other things|"
    r"as (?:mentioned|discussed|noted) earlier|"
    r"as I (?:said|mentioned)|"
    r"the changes? (?:above|below)|"
    r"various (?:updates|fixes|changes)"
    r")"
)

VISIBLE_WIN_RE = re.compile(
    r"(?i)\b("
    r"now works|"
    r"works (?:now|with)|"
    r"you can (?:now )?(?:run|open|try|use)|"
    r"try\s*:|"
    r"verify\s*:|"
    r"confirm\s*:|"
    r"should (?:now )?see|"
    r"login now|"
    r"passing|"
    r"green"
    r")\b|"
    r"^(?:try|run|open|verify)\b"
)


class VisibleWinsRule(Rule):
    name = "visible_wins"
    description = (
        "Multi-turn: when prior work claimed completion, show what now works "
        "in concrete terms — do not bury wins in a vague recap."
    )
    weight = 1.2
    multi_turn_only = True

    def _check(self, context: ScoreContext) -> RuleResult:
        prior = context.prior_assistant
        if not prior:
            return RuleResult.not_applicable("no prior assistant turn")

        prior_body = prose(prior)
        # Applicable when prior turn claimed completed work, OR current response is a recap
        response = prose(context.response)
        prior_claimed = bool(COMPLETION_CLAIM_RE.search(prior_body))
        current_recap = bool(BURIED_RECAP_RE.search(response))

        if not prior_claimed and not current_recap:
            return RuleResult.not_applicable("no completion claim to make visible")

        if BURIED_RECAP_RE.search(response) and not VISIBLE_WIN_RE.search(response):
            match = BURIED_RECAP_RE.search(response)
            return RuleResult.failed(match.group(0) if match else "buried recap")

        if VISIBLE_WIN_RE.search(response):
            return RuleResult.passed()

        # First line is a concrete try/run also counts
        line = first_line(context.response)
        if line and VISIBLE_WIN_RE.search(line):
            return RuleResult.passed()

        if prior_claimed:
            return RuleResult.failed("completion claimed earlier but win not made visible")

        return RuleResult.not_applicable("no visible-win obligation detected")
