"""Anthropic Messages API adapter (optional httpx extra)."""

from __future__ import annotations

import os

from burybench.providers.base import ProviderAdapter


class AnthropicProvider(ProviderAdapter):
    name = "anthropic"

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com"
        ).rstrip("/")
        self.max_tokens = max_tokens
        if not self.api_key:
            raise EnvironmentError(
                "Missing API key. Set environment variable ANTHROPIC_API_KEY "
                "(or pass api_key=...)."
            )

    def send(self, prompt: str) -> str:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "The anthropic provider requires httpx. "
                "Install with: pip install 'bury-bench[providers]'"
            ) from exc

        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        try:
            parts = data["content"]
            texts = [p["text"] for p in parts if p.get("type") == "text"]
            if not texts:
                raise KeyError("no text blocks")
            return "\n".join(texts)
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Anthropic response shape: {data!r}") from exc
