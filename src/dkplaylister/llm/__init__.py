"""LLM provider system for DKPlaylister.

Usage:
    from dkplaylister.llm import get_provider

    provider = get_provider("grok")  # or "openai", etc.
    pitch = provider.generate_pitch(...)
"""

from __future__ import annotations

from typing import Optional

from dkplaylister.llm.base import LLMProvider
from dkplaylister.llm.grok import GrokProvider


def get_provider(
    provider: str = "grok",
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Factory for LLM providers.

    Currently only Grok is implemented.
    """

    provider = provider.lower()

    if provider in ("grok", "xai"):
        return GrokProvider(model=model or "grok-3", **kwargs)

    # Future providers will be added here
    # if provider == "openai":
    #     from .openai import OpenAIProvider
    #     return OpenAIProvider(...)

    raise ValueError(f"Unknown LLM provider: {provider}")
