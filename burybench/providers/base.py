"""Provider adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderAdapter(ABC):
    """Thin adapter: send a prompt, get a response string back."""

    name: str

    @abstractmethod
    def send(self, prompt: str) -> str:
        """Send *prompt* and return the model/agent response text."""
