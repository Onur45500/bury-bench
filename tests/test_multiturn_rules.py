"""Tests for multi-turn rules 5 (restate_state) and 7 (visible_wins)."""

from __future__ import annotations

import pytest

from burybench.rules.base import RuleStatus, ScoreContext, Turn
from burybench.rules.restate_state import RestateStateRule
from burybench.rules.visible_wins import VisibleWinsRule


def _ctx(response: str, prior: str | None = None) -> ScoreContext:
    turns: tuple[Turn, ...] = ()
    if prior is not None:
        turns = (
            Turn(role="user", content="continue"),
            Turn(role="assistant", content=prior),
            Turn(role="user", content="ok next"),
        )
    return ScoreContext(response=response, turns=turns)


# --- restate_state ---


def test_restate_state_na_single_turn() -> None:
    result = RestateStateRule().check("Step 3 of 5 done.")
    assert result.status == RuleStatus.NOT_APPLICABLE


def test_restate_state_na_no_prior_state() -> None:
    result = RestateStateRule().check(
        "Run the tests.",
        context=_ctx("Run the tests.", prior="Here is some general advice."),
    )
    assert result.status == RuleStatus.NOT_APPLICABLE


@pytest.mark.parametrize(
    "response",
    [
        "Step 3 of 5 done: schema updated. Next: backfill the new column.",
        "Step 3 of 5 complete. Run `python backfill.py`.",
    ],
)
def test_restate_state_pass(response: str) -> None:
    prior = "Step 3 of 5 done: schema updated. Next: backfill the new column."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "response",
    [
        "Done. Ready for the next part?",
        "Ok continuing. Run the script when you can.",
    ],
)
def test_restate_state_fail(response: str) -> None:
    prior = "Step 3 of 5 done: schema updated. Next: backfill the new column."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_restate_state_pass_artifact_overlap() -> None:
    prior = "Fixed `src/auth.ts`. Login tests passing."
    response = "Login now works. Try `src/auth.ts` path again with a fresh token."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


def test_restate_state_fail_missing_artifact() -> None:
    prior = "Updated `src/auth.ts` and finished the token check."
    response = "Moving on to the next module now."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.FAILED


def test_restate_state_pass_command_overlap() -> None:
    prior = "Fixed the suite hook. Run `pytest tests/test_auth.py` next."
    response = "Auth green. Re-run `pytest tests/test_auth.py` to confirm."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


def test_restate_state_pass_checklist_overlap() -> None:
    prior = """Progress:
- [x] schema updated
- [ ] backfill rows
Next: backfill.
"""
    response = "Schema updated is done. Next: backfill the rows."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


def test_restate_state_pass_paraphrase() -> None:
    prior = "Schema updated. Ready for the backfill script."
    response = "Migration applied on staging. Run `python backfill.py`."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


def test_restate_state_fail_empty_continuer() -> None:
    prior = "Step 2 of 4 done: schema updated in `migrations/002.sql`."
    response = "ok next"
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.FAILED
    assert "continuer" in (result.evidence or "")


def test_restate_state_pass_artifact_without_echoing_step() -> None:
    # Step present in prior, but restating the artifact is enough
    prior = "Step 2 of 4 done: patched `src/auth.ts`."
    response = "Continue from `src/auth.ts`. Run the auth suite."
    result = RestateStateRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


# --- visible_wins ---


def test_visible_wins_na_single_turn() -> None:
    result = VisibleWinsRule().check("Login now works. Try `/login`.")
    assert result.status == RuleStatus.NOT_APPLICABLE


def test_visible_wins_na_no_completion() -> None:
    prior = "Looking into the stack next."
    response = "Still investigating."
    result = VisibleWinsRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.NOT_APPLICABLE


@pytest.mark.parametrize(
    "response",
    [
        "Login now works with magic links. Try: `npm run dev`, open `/login`.",
        "Auth is fixed. You can now run `npm test -- auth.spec.ts`.",
    ],
)
def test_visible_wins_pass(response: str) -> None:
    prior = "I've fixed the auth header check in the middleware."
    result = VisibleWinsRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "response",
    [
        "I've made some changes to the auth flow. Among other things it should be better.",
        "As mentioned earlier, various updates were applied.",
    ],
)
def test_visible_wins_fail_buried_recap(response: str) -> None:
    prior = "I've done the token patch."
    result = VisibleWinsRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_visible_wins_fail_prior_claim_no_visibility() -> None:
    prior = "I've fixed the null check and updated the handler."
    response = "We can continue whenever you're ready."
    result = VisibleWinsRule().check(response, context=_ctx(response, prior=prior))
    assert result.status == RuleStatus.FAILED
