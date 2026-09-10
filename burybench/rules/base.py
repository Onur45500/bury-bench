"""Rule interface and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class RuleStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class RuleResult:
    status: RuleStatus
    evidence: str | None = None

    @classmethod
    def passed(cls) -> RuleResult:
        return cls(status=RuleStatus.PASSED)

    @classmethod
    def failed(cls, evidence: str) -> RuleResult:
        return cls(status=RuleStatus.FAILED, evidence=evidence)

    @classmethod
    def not_applicable(cls, reason: str | None = None) -> RuleResult:
        return cls(status=RuleStatus.NOT_APPLICABLE, evidence=reason)


@dataclass(frozen=True)
class Turn:
    role: str  # user | assistant
    content: str


@dataclass(frozen=True)
class ScoreContext:
    """Response under test plus optional multi-turn history."""

    response: str
    turns: tuple[Turn, ...] = field(default_factory=tuple)

    @property
    def prior_assistant(self) -> str | None:
        """Most recent assistant turn before the response under test."""
        for turn in reversed(self.turns):
            if turn.role == "assistant":
                return turn.content
        return None

    @property
    def is_multi_turn(self) -> bool:
        return any(t.role == "assistant" for t in self.turns)


class Rule(ABC):
    """Deterministic check against a response. Weight is scorer config, not observation."""

    name: str
    description: str
    weight: float = 1.0
    # If True, rule is N/A on single-turn (no prior assistant context).
    multi_turn_only: bool = False

    def check(self, text: str, *, context: ScoreContext | None = None) -> RuleResult:
        """Evaluate *text* (the new assistant response). Optional multi-turn *context*."""
        ctx = context or ScoreContext(response=text)
        if self.multi_turn_only and not ctx.is_multi_turn:
            return RuleResult.not_applicable("single-turn; multi-turn context required")
        return self._check(ctx)

    @abstractmethod
    def _check(self, context: ScoreContext) -> RuleResult:
        """Implement the rule against a ScoreContext."""
