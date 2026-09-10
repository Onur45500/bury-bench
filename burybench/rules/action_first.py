"""Rule 1: Lead with the next action."""

from __future__ import annotations

import re

from burybench.rules.base import Rule, RuleResult, ScoreContext
from burybench.rules.textprep import first_line

# Imperative verbs commonly used as first-word actions in coding answers
IMPERATIVE_VERBS = frozenset(
    {
        "run",
        "open",
        "edit",
        "replace",
        "add",
        "remove",
        "delete",
        "install",
        "uninstall",
        "update",
        "upgrade",
        "create",
        "write",
        "fix",
        "change",
        "set",
        "check",
        "verify",
        "test",
        "restart",
        "stop",
        "start",
        "move",
        "copy",
        "paste",
        "type",
        "click",
        "navigate",
        "go",
        "use",
        "call",
        "import",
        "export",
        "clone",
        "pull",
        "push",
        "commit",
        "build",
        "deploy",
        "configure",
        "enable",
        "disable",
        "restart",
        "retry",
        "rerun",
        "reinstall",
        "downgrade",
        "pin",
        "bump",
        "patch",
        "apply",
        "insert",
        "swap",
        "rename",
        "mkdir",
        "cd",
        "pip",
        "npm",
        "yarn",
        "pnpm",
        "cargo",
        "apt",
        "brew",
        "docker",
        "kubectl",
        "git",
        "curl",
        "wget",
        "python",
        "node",
        "next",
    }
)

# Path-like or command-like tokens on the first line
CODE_OR_PATH_RE = re.compile(
    r"("
    r"`[^`]+`"  # inline code
    r"|```"  # fenced start
    r"|[/\\][\w./\\-]+\.\w+"  # path with extension
    r"|[\w-]+/[\w./-]+"  # path-ish
    r"|^[A-Za-z]:\\[\w\\./-]+"  # windows path
    r")"
)


class ActionFirstRule(Rule):
    name = "action_first"
    description = (
        "First non-empty line is something the reader can do "
        "(command, path, code span, or imperative verb)."
    )
    weight = 1.5

    def _check(self, context: ScoreContext) -> RuleResult:
        text = context.response
        line = first_line(text)
        if line is None:
            return RuleResult.not_applicable("empty response")

        if CODE_OR_PATH_RE.search(line):
            return RuleResult.passed()

        first_word = re.match(r"^[\W_]*([A-Za-z]+)", line)
        if first_word and first_word.group(1).lower() in IMPERATIVE_VERBS:
            return RuleResult.passed()

        # "Next:" directive counts as action-leading
        if re.match(r"(?i)^next\s*:", line):
            return RuleResult.passed()

        return RuleResult.failed(line[:120])
