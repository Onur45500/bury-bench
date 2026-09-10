"""Paste provider — interactive or scripted stdin, zero API dependencies."""

from __future__ import annotations

import sys

from burybench.providers.base import ProviderAdapter


class PasteProvider(ProviderAdapter):
    """Read a response from stdin. End with a line containing only END."""

    name = "paste"

    def __init__(self, *, input_fn=None, output_fn=None) -> None:
        self._input = input_fn or input
        self._output = output_fn or (lambda s: print(s, file=sys.stderr))

    def send(self, prompt: str) -> str:
        self._output("=" * 60)
        self._output("FIXTURE PROMPT:")
        self._output(prompt)
        self._output("=" * 60)
        self._output("Paste the agent response below.")
        self._output("Finish with a line containing only: END")
        self._output("-" * 60)

        lines: list[str] = []
        while True:
            try:
                line = self._input()
            except EOFError:
                break
            if line.strip() == "END":
                break
            lines.append(line)

        response = "\n".join(lines).strip()
        if not response:
            raise ValueError("Empty pasted response")
        return response
