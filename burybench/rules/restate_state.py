"""Rule 5: Restate state every turn (multi-turn only)."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

# Patterns that establish progress/state in a prior assistant turn
STEP_STATE_RE = re.compile(
    r"(?i)\bstep\s+(\d+)\s*(?:of|/)\s*(\d+)\b|"
    r"\b(\d+)\s*(?:of|/)\s*(\d+)\s+(?:done|complete|finished)\b"
)
DONE_MARKER_RE = re.compile(
    r"(?i)\b("
    r"done|complete|completed|finished|updated|fixed|added|created|"
    r"schema updated|migration applied|tests? pass(?:ing|ed)?"
    r")\b"
)
# Concrete artifact tokens worth restating
ARTIFACT_RE = re.compile(
    r"(?:"
    r"`[^`]+`"
    r"|[\w.-]+\.(?:ts|tsx|js|jsx|py|go|rs|java|sql|yml|yaml|json|toml|md)"
    r"|/(?:[\w.-]+/)*[\w.-]+"
    r")"
)


def _has_progress_claim(prior: str) -> bool:
    body = prose(prior)
    if STEP_STATE_RE.search(body):
        return True
    # Check artifacts on raw text — prose() strips inline code
    if DONE_MARKER_RE.search(body) and (
        ARTIFACT_RE.search(prior) or re.search(r"(?i)\bstep\b", body)
    ):
        return True
    return False


def _extract_state_tokens(prior: str) -> list[str]:
    tokens: list[str] = []
    for match in STEP_STATE_RE.finditer(prior):
        tokens.append(match.group(0))
    for match in ARTIFACT_RE.finditer(prior):
        tok = match.group(0)
        if tok not in tokens:
            tokens.append(tok)
    return tokens


class RestateStateRule(Rule):
    name = "restate_state"
    description = (
        "Multi-turn: restate established step progress and named artifacts; "
        "do not assume the reader remembers prior turns."
    )
    weight = 1.3
    multi_turn_only = True

    def _check(self, context: ScoreContext) -> RuleResult:
        prior = context.prior_assistant
        if not prior:
            return RuleResult.not_applicable("no prior assistant turn")

        if not _has_progress_claim(prior):
            return RuleResult.not_applicable("prior turn established no restatable state")

        tokens = _extract_state_tokens(prior)
        # Use raw response so inline-code artifacts remain visible for overlap checks
        response_raw = context.response
        response_prose = prose(response_raw)

        # Prefer explicit step restatement when prior had step N of M
        step_match = STEP_STATE_RE.search(prose(prior))
        if step_match:
            if STEP_STATE_RE.search(response_prose) or STEP_STATE_RE.search(response_raw):
                return RuleResult.passed()
            if re.search(r"(?i)\bstep\s+\d+\b", response_prose) and DONE_MARKER_RE.search(
                response_prose
            ):
                return RuleResult.passed()
            return RuleResult.failed(
                f"prior state {step_match.group(0)!r} not restated"
            )

        if not tokens:
            return RuleResult.not_applicable("no extractable state tokens")

        prior_arts = [t.strip("`") for t in tokens]
        resp_plain = response_raw.replace("`", "")
        hits = [a for a in prior_arts if a and a in resp_plain]

        if hits:
            return RuleResult.passed()

        preview = ", ".join(prior_arts[:3])
        return RuleResult.failed(f"missing restatement of: {preview}")
