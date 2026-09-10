"""OpenAI-compatible chat completions adapter (optional httpx extra)."""

from __future__ import annotations

import os

from burybench.providers.base import ProviderAdapter


class OpenAICompatProvider(ProviderAdapter):
    """Works with OpenAI and any OpenAI-compatible /v1/chat/completions endpoint."""

    name = "openai"

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        if not self.api_key:
            raise EnvironmentError(
                "Missing API key. Set environment variable OPENAI_API_KEY "
                "(or pass api_key=...)."
            )

    def send(self, prompt: str) -> str:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "The openai provider requires httpx. "
                "Install with: pip install 'bury-bench[providers]'"
            ) from exc

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected OpenAI-compatible response shape: {data!r}") from exc
