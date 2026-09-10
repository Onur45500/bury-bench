"""Provider factory."""

from __future__ import annotations

from burybench.providers.base import ProviderAdapter
from burybench.providers.local_paste import PasteProvider


def get_provider(
    name: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> ProviderAdapter:
    key = name.lower().strip()
    if key in {"paste", "local_paste", "local"}:
        return PasteProvider()
    if key in {"openai", "openai_compat", "openai-compat"}:
        if not model:
            raise ValueError("--model is required for the openai provider")
        from burybench.providers.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(model=model, base_url=base_url)
    if key == "anthropic":
        if not model:
            raise ValueError("--model is required for the anthropic provider")
        from burybench.providers.anthropic import AnthropicProvider

        return AnthropicProvider(model=model, base_url=base_url)
    raise ValueError(
        f"Unknown provider {name!r}. Choose: paste, openai, anthropic."
    )


__all__ = ["ProviderAdapter", "PasteProvider", "get_provider"]
