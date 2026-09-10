"""Rule 5: Restate state every turn (multi-turn only).

State card from the prior assistant turn:
- step N of M markers
- path / backtick artifacts
- commands in backticks
- checklist / plan lines
- progress paraphrase keys (schema/migration/auth, etc.)

Pass if the new response overlaps any of those signals.
Fail pure continuers ("ok next") when prior state existed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import prose

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
ARTIFACT_RE = re.compile(
    r"(?:"
    r"`[^`]+`"
    r"|[\w.-]+\.(?:ts|tsx|js|jsx|py|go|rs|java|sql|yml|yaml|json|toml|md)"
    r"|/(?:[\w.-]+/)*[\w.-]+"
    r")"
)
CHECKLIST_RE = re.compile(
    r"(?m)^\s*(?:[-*]|\d+[.)]|\[\s*[xX ]\s*\])\s+(.+)$"
)
COMMAND_RE = re.compile(
    r"`((?:npm|npx|pnpm|yarn|pip|poetry|cargo|pytest|python|node|git|docker|"
    r"kubectl|uv|bun)[^`]*)`"
)
EMPTY_CONTINUER_RE = re.compile(
    r"(?is)^\s*(?:(?:ok(?:ay)?|sure|continuing|continue|next|done|ready|got it)"
    r"\s*[.!]?\s*)+$"
)

# (prior_pattern, response_pattern) paraphrase pairs
PARAPHRASE_PAIRS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (
        re.compile(r"(?i)\bschema updated\b"),
        re.compile(r"(?i)\b(schema|migration|column).{0,48}(updated|applied|nullable|added)\b"),
    ),
    (
        re.compile(r"(?i)\bmigration applied\b"),
        re.compile(r"(?i)\b(migration|schema|backfill).{0,48}(applied|done|ran|complete)\b"),
    ),
    (
        re.compile(r"(?i)\b(auth|login|token).{0,24}(fixed|updated|patched)\b"),
        re.compile(r"(?i)\b(auth|login|token|middleware).{0,48}(fixed|works|updated|ok)\b"),
    ),
    (
        re.compile(r"(?i)\bnull(?:able)?\s+column\b"),
        re.compile(r"(?i)\b(column|field).{0,32}(nullable|null|added)\b"),
    ),
]


@dataclass
class StateCard:
    steps: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    paraphrase_priors: list[re.Pattern[str]] = field(default_factory=list)

    @property
    def has_signal(self) -> bool:
        return bool(
            self.steps
            or self.artifacts
            or self.commands
            or self.checklist
            or self.paraphrase_priors
        )


def _strip_ticks(token: str) -> str:
    return token.strip().strip("`")


def build_state_card(prior: str) -> StateCard:
    card = StateCard()
    for match in STEP_STATE_RE.finditer(prior):
        card.steps.append(match.group(0))
    for match in ARTIFACT_RE.finditer(prior):
        tok = _strip_ticks(match.group(0))
        if tok and tok not in card.artifacts:
            card.artifacts.append(tok)
    for match in COMMAND_RE.finditer(prior):
        cmd = match.group(1).strip()
        if cmd and cmd not in card.commands:
            card.commands.append(cmd)
    for match in CHECKLIST_RE.finditer(prior):
        item = match.group(1).strip()
        if item and item not in card.checklist:
            card.checklist.append(item)
    for prior_re, _resp_re in PARAPHRASE_PAIRS:
        if prior_re.search(prior):
            card.paraphrase_priors.append(prior_re)
    return card


def _has_progress_claim(prior: str, card: StateCard) -> bool:
    body = prose(prior)
    if STEP_STATE_RE.search(body):
        return True
    if card.checklist and DONE_MARKER_RE.search(body):
        return True
    if card.checklist and any(
        re.search(r"(?i)\b(done|fixed|updated|added|complete)\b", item) for item in card.checklist
    ):
        return True
    if DONE_MARKER_RE.search(body) and (
        card.artifacts or card.commands or re.search(r"(?i)\bstep\b", body)
    ):
        return True
    if card.paraphrase_priors:
        return True
    return False


def _checklist_overlap(response: str, items: list[str]) -> list[str]:
    resp = response.lower()
    hits: list[str] = []
    for item in items:
        # Require a meaningful token from the checklist line
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", item)
        if any(tok.lower() in resp for tok in tokens[:4]):
            hits.append(item)
    return hits


def _covers_state(response_raw: str, card: StateCard) -> tuple[bool, str | None]:
    response_prose = prose(response_raw)
    resp_plain = response_raw.replace("`", "")

    if card.steps:
        if STEP_STATE_RE.search(response_prose) or STEP_STATE_RE.search(response_raw):
            return True, None
        if re.search(r"(?i)\bstep\s+\d+\b", response_prose) and DONE_MARKER_RE.search(
            response_prose
        ):
            return True, None
        # Fall through: artifact/command/paraphrase can still rescue

    art_hits = [a for a in card.artifacts if a and a in resp_plain]
    if art_hits:
        return True, None

    cmd_hits = [c for c in card.commands if c and c in resp_plain]
    if cmd_hits:
        return True, None

    check_hits = _checklist_overlap(resp_plain, card.checklist)
    if check_hits:
        return True, None

    for prior_re, resp_re in PARAPHRASE_PAIRS:
        if prior_re in card.paraphrase_priors and resp_re.search(response_raw):
            return True, None

    if card.steps:
        return False, f"prior state {card.steps[0]!r} not restated"

    preview_bits = (card.artifacts + card.commands + card.checklist)[:3]
    if preview_bits:
        return False, f"missing restatement of: {', '.join(preview_bits)}"
    return False, "prior progress not restated"


class RestateStateRule(Rule):
    name = "restate_state"
    description = (
        "Multi-turn: restate step progress, artifacts, commands, or checklist "
        "items from the prior turn (paraphrase allowed for known progress keys)."
    )
    weight = 1.3
    multi_turn_only = True

    def _check(self, context: ScoreContext) -> RuleResult:
        prior = context.prior_assistant
        if not prior:
            return RuleResult.not_applicable("no prior assistant turn")

        card = build_state_card(prior)
        if not _has_progress_claim(prior, card) or not card.has_signal:
            return RuleResult.not_applicable("prior turn established no restatable state")

        response_raw = context.response
        if EMPTY_CONTINUER_RE.match(prose(response_raw).strip()):
            return RuleResult.failed("empty continuer; prior state not restated")

        ok, evidence = _covers_state(response_raw, card)
        if ok:
            return RuleResult.passed()
        return RuleResult.failed(evidence or "prior state not restated")
