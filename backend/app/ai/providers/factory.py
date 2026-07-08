"""Provider factory — returns the right LLMProvider based on config.

The application starts normally when no LLM_API_KEY is set; in that case the
FakeLLMProvider is returned and AI endpoints return a clear controlled
service-unavailable response rather than crashing.
"""
from __future__ import annotations

import functools
from typing import Union

from .base import LLMProvider
from .fake import FakeLLMProvider
from .openai_compat import OpenAICompatProvider

_OPENAI_BASE = "https://api.openai.com/v1"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _build_provider() -> LLMProvider:
    from app.config import settings  # local import — avoids circular at module load

    provider = (settings.LLM_PROVIDER or "mock").lower()
    api_key = settings.LLM_API_KEY or ""
    model = settings.LLM_MODEL or "mock-model"
    base_url = settings.LLM_BASE_URL or ""

    if provider == "mock" or not api_key:
        return FakeLLMProvider()

    if provider == "openai":
        return OpenAICompatProvider(
            api_key=api_key,
            model=model,
            base_url=base_url or _OPENAI_BASE,
            provider_label="openai",
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )

    if provider == "openrouter":
        return OpenAICompatProvider(
            api_key=api_key,
            model=model,
            base_url=base_url or _OPENROUTER_BASE,
            provider_label="openrouter",
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )

    if provider == "anthropic":
        # Anthropic uses an OpenAI-compatible proxy via OpenRouter or the
        # messages API.  If the user has pointed LLM_BASE_URL at an OpenAI-
        # compatible proxy (e.g. OpenRouter) we reuse that adapter.
        if base_url:
            return OpenAICompatProvider(
                api_key=api_key,
                model=model,
                base_url=base_url,
                provider_label="anthropic",
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )
        # Native Anthropic not yet implemented — fall back to fake with clear log
        import logging
        logging.getLogger(__name__).warning(
            "Native Anthropic provider not yet implemented; falling back to fake provider. "
            "Set LLM_BASE_URL to an OpenAI-compatible proxy to use Anthropic."
        )
        return FakeLLMProvider()

    # Unknown provider — fail safe
    import logging
    logging.getLogger(__name__).warning(
        "Unknown LLM_PROVIDER=%r; falling back to fake provider.", provider
    )
    return FakeLLMProvider()


@functools.lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return a cached singleton provider.  Call ``reset_provider()`` in tests
    to clear the cache after patching settings."""
    return _build_provider()


def reset_provider() -> None:
    """Clear the cached provider (useful in tests)."""
    get_llm_provider.cache_clear()
