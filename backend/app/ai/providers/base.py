from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    max_tokens: int = 2000
    temperature: float = 0.0


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: float = 0.0


class ProviderUnavailableError(Exception):
    """Raised when the LLM provider is not configured or unreachable."""


class ProviderTimeoutError(ProviderUnavailableError):
    """Raised when the LLM provider call times out."""


class ProviderAuthError(ProviderUnavailableError):
    """Raised when the LLM provider rejects credentials."""


class ProviderRateLimitError(ProviderUnavailableError):
    """Raised when the LLM provider returns a rate-limit error."""


@runtime_checkable
class LLMProvider(Protocol):
    """Sync LLM provider interface.  All methods are synchronous to match the
    rest of the FastAPI/SQLAlchemy synchronous stack."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def generate(self, request: LLMRequest) -> LLMResponse: ...
