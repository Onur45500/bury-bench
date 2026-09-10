"""Unit tests for every rule: ≥2 pass, ≥2 fail, plus N/A where applicable."""

from __future__ import annotations

import pytest

from burybench.rules.action_first import ActionFirstRule
from burybench.rules.base import RuleStatus
from burybench.rules.capped_lists import CappedListsRule
from burybench.rules.error_tone import ErrorToneRule
from burybench.rules.no_closer import NoCloserRule
from burybench.rules.no_hedge_filler import NoHedgeFillerRule
from burybench.rules.no_idiom import NoIdiomRule
from burybench.rules.no_preamble import NoPreambleRule
from burybench.rules.no_tangent import NoTangentRule
from burybench.rules.numbered_steps import NumberedStepsRule
from burybench.rules.one_next_action import OneNextActionRule
from burybench.rules.time_estimate import TimeEstimateRule


# --- action_first ---


@pytest.mark.parametrize(
    "text",
    [
        "Run `npm install jsonwebtoken`, then edit `src/auth.ts:42`.",
        "Open `src/auth.ts` and replace the verify function.",
        "Next: paste the first failing test line.",
        "`pip install fastapi` and restart the server.",
    ],
)
def test_action_first_pass(text: str) -> None:
    assert ActionFirstRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Let's think about this. Your auth flow has a few moving pieces...",
        "Great question! There are several ways to approach this.",
        "The issue appears to be related to how tokens are validated.",
        "Looking at your traceback, something interesting is going on.",
    ],
)
def test_action_first_fail(text: str) -> None:
    result = ActionFirstRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


# --- numbered_steps ---


def test_numbered_steps_pass_with_list() -> None:
    text = """
1. Open `src/auth.ts`
2. Replace `verifyToken` (lines 42 to 58)
3. Run `npm test -- auth.spec.ts`
"""
    assert NumberedStepsRule().check(text).status == RuleStatus.PASSED


def test_numbered_steps_pass_single_action() -> None:
    result = NumberedStepsRule().check("Run `npm test`.")
    assert result.status == RuleStatus.NOT_APPLICABLE


def test_numbered_steps_fail_prose_sequence() -> None:
    text = (
        "First open the file, then find the function, "
        "after that swap it out, finally run the tests."
    )
    result = NumberedStepsRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_numbered_steps_fail_then_next() -> None:
    text = "Install the package then restart the server. Next, check the logs."
    result = NumberedStepsRule().check(text)
    assert result.status == RuleStatus.FAILED


# --- one_next_action ---


def test_one_next_action_pass() -> None:
    text = (
        "Login now works with magic links.\n\n"
        "Next: run `npm run dev` and open `/login`."
    )
    assert OneNextActionRule().check(text).status == RuleStatus.PASSED


def test_one_next_action_pass_run() -> None:
    text = "Cause: missing header.\n\nRun `pytest tests/test_auth.py` and paste the failure."
    assert OneNextActionRule().check(text).status == RuleStatus.PASSED


def test_one_next_action_fail_options() -> None:
    text = (
        "You could try several approaches.\n\n"
        "If you want, feel free to pick whichever option you prefer."
    )
    result = OneNextActionRule().check(text)
    assert result.status == RuleStatus.FAILED


def test_one_next_action_fail_soft_close() -> None:
    text = "That should fix it.\n\nLet me know if you want to dig deeper."
    result = OneNextActionRule().check(text)
    assert result.status == RuleStatus.FAILED


def test_one_next_action_na_closed() -> None:
    result = OneNextActionRule().check("Fixed. Auth header added.")
    assert result.status == RuleStatus.NOT_APPLICABLE


# --- no_tangent ---


@pytest.mark.parametrize(
    "text",
    [
        "Here's the fix. Update line 42 to include the header.",
        "Cause: missing import. Add `import jwt` at the top.",
    ],
)
def test_no_tangent_pass(text: str) -> None:
    assert NoTangentRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Here's the fix. By the way, your dependency is also stale.",
        "Done. Also worth noting: your README is out of date.",
        "Fixed. While we're at it, you should upgrade Node.",
        "Patched. On a side note, consider adding tests.",
    ],
)
def test_no_tangent_fail(text: str) -> None:
    result = NoTangentRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


# --- time_estimate ---


def test_time_estimate_na() -> None:
    result = TimeEstimateRule().check("Run `npm install` and restart.")
    assert result.status == RuleStatus.NOT_APPLICABLE


def test_time_estimate_pass_concrete() -> None:
    text = "About 15 minutes if tests already cover this. An afternoon if not."
    assert TimeEstimateRule().check(text).status == RuleStatus.PASSED


def test_time_estimate_fail_vague() -> None:
    text = "This will take some work to get right."
    result = TimeEstimateRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_time_estimate_fail_a_while() -> None:
    text = "The migration should take a while depending on data size."
    result = TimeEstimateRule().check(text)
    assert result.status == RuleStatus.FAILED


# --- error_tone ---


@pytest.mark.parametrize(
    "text",
    [
        "Test fails at `auth.spec.ts:42`: expected 200, got 401.",
        "Cause: missing auth header. Fix: add Authorization bearer token.",
    ],
)
def test_error_tone_pass(text: str) -> None:
    assert ErrorToneRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Uh oh, the test is failing.",
        "Oh no, something went wrong with the build.",
        "There seems to be a problem with your configuration.",
        "Yikes, the types don't match.",
    ],
)
def test_error_tone_fail(text: str) -> None:
    result = ErrorToneRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


# --- capped_lists ---


def test_capped_lists_pass() -> None:
    text = """
- one
- two
- three
- four
- five
"""
    assert CappedListsRule().check(text).status == RuleStatus.PASSED


def test_capped_lists_pass_numbered() -> None:
    text = """
1. alpha
2. beta
3. gamma
"""
    assert CappedListsRule().check(text).status == RuleStatus.PASSED


def test_capped_lists_fail() -> None:
    text = """
- one
- two
- three
- four
- five
- six
"""
    result = CappedListsRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert "6" in (result.evidence or "")


def test_capped_lists_na() -> None:
    result = CappedListsRule().check("Just a paragraph, no list.")
    assert result.status == RuleStatus.NOT_APPLICABLE


# --- no_preamble ---


@pytest.mark.parametrize(
    "text",
    [
        "Run `pip install pydantic` and restart the worker.",
        "Missing null check on line 18. Add `if user is None: return`.",
    ],
)
def test_no_preamble_pass(text: str) -> None:
    assert NoPreambleRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Great question! Here's how I'd approach it.",
        "Let me look at your stack trace carefully.",
        "I'll walk you through the options.",
        "Sure! You can fix this a few ways.",
        "Looking at your error, the path is wrong.",
        "To answer your question, use a transaction.",
    ],
)
def test_no_preamble_fail(text: str) -> None:
    result = NoPreambleRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


# --- no_closer ---


@pytest.mark.parametrize(
    "text",
    [
        "Run `npm test` and paste the first failing line.",
        "Cause: wrong import path.\n\nFix: change to `./utils/auth`.",
    ],
)
def test_no_closer_pass(text: str) -> None:
    assert NoCloserRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Update the config.\n\nHope this helps!",
        "Done.\n\nLet me know if you need anything else.",
        "Fixed the type error.\n\nFeel free to ask if you have questions.",
        "That should work.\n\nHappy to clarify further.",
    ],
)
def test_no_closer_fail(text: str) -> None:
    result = NoCloserRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


# --- no_hedge_filler ---


def test_no_hedge_pass_clean() -> None:
    text = "The auth header is missing. Add `Authorization: Bearer ${token}`."
    assert NoHedgeFillerRule().check(text).status == RuleStatus.PASSED


def test_no_hedge_pass_sparse() -> None:
    # One hedge late in a long response stays under the density threshold
    words = " ".join(["word"] * 150)
    text = f"The root cause is a missing import. {words} It might need a restart."
    assert NoHedgeFillerRule().check(text).status == RuleStatus.PASSED


def test_no_hedge_fail_dense() -> None:
    text = (
        "This might be a config issue. Perhaps the path is wrong. "
        "Maybe you could possibly check the env. It seems like a kind of race."
    )
    result = NoHedgeFillerRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_no_hedge_fail_opening_cluster_in_long_reply() -> None:
    # Density can look fine if the body is long — opening cluster must still fail
    pad = " ".join(["detail"] * 200)
    text = (
        f"This might be the wrong host. Perhaps the proxy is misconfigured. {pad}"
    )
    result = NoHedgeFillerRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert "opening" in (result.evidence or "")


def test_no_hedge_pass_short_honest_single() -> None:
    text = "This might be a race. Paste the next failing log line."
    assert NoHedgeFillerRule().check(text).status == RuleStatus.PASSED


def test_no_hedge_pass_diagnostic_allowlist() -> None:
    text = (
        "Root cause is unclear. It might be the cache, unknown until we see "
        "the next trace. Run `pytest -k cache` and paste the failure."
    )
    # "might" sits in a diagnostic sentence → not counted; remaining clean
    assert NoHedgeFillerRule().check(text).status == RuleStatus.PASSED


def test_no_hedge_ignores_code() -> None:
    # Hedge words inside code must not count
    text = (
        "Add this comment and ship it.\n\n"
        "```python\n# perhaps refactor this later\nx = might_be_none\n```\n"
    )
    assert NoHedgeFillerRule().check(text).status == RuleStatus.PASSED


# --- no_idiom ---


@pytest.mark.parametrize(
    "text",
    [
        "Replace the handler and rerun the suite.",
        "Add a null check before dereferencing the user object.",
    ],
)
def test_no_idiom_pass(text: str) -> None:
    assert NoIdiomRule().check(text).status == RuleStatus.PASSED


@pytest.mark.parametrize(
    "text",
    [
        "Let's circle back to the auth issue after lunch.",
        "We should get the ball rolling on the migration.",
        "Make sure we're on the same page about the schema.",
        "Start with the low-hanging fruit in the test suite.",
    ],
)
def test_no_idiom_fail(text: str) -> None:
    result = NoIdiomRule().check(text)
    assert result.status == RuleStatus.FAILED
    assert result.evidence


def test_no_idiom_ignores_code() -> None:
    text = (
        "Ship the patch.\n\n"
        "```\n# TODO: circle back to optimize\n```\n"
    )
    assert NoIdiomRule().check(text).status == RuleStatus.PASSED
