"""OpenAI-compatible provider adapter (supports OpenAI and OpenRouter)."""
from __future__ import annotations

import time
import json
from typing import Optional

import httpx

from .base import (
    LLMRequest,
    LLMResponse,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


_OPENAI_BASE = "https://api.openai.com/v1"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_TIMEOUT_SECONDS = 30
_MAX_RETRIES = 2
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class OpenAICompatProvider:
    """Calls any OpenAI-compatible /chat/completions endpoint.

    Works for: OpenAI, OpenRouter (same API shape, different base URL and
    auth header conventions).
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        provider_label: str = "openai",
        max_tokens: int = 2000,
        temperature: float = 0.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or _OPENAI_BASE).rstrip("/")
        self._provider_label = provider_label
        self._max_tokens = max_tokens
        self._temperature = temperature

    @property
    def provider_name(self) -> str:
        return self._provider_label

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "max_tokens": min(request.max_tokens, self._max_tokens),
            "temperature": request.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter" in self._base_url:
            headers["HTTP-Referer"] = "https://amad.construction"
            headers["X-Title"] = "Amad Construction Intelligence"

        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                start = time.monotonic()
                with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
                    resp = client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 401:
                    raise ProviderAuthError("Invalid API key")
                if resp.status_code == 429:
                    raise ProviderRateLimitError("Provider rate limit exceeded")
                if resp.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                    last_error = ProviderUnavailableError(
                        f"Provider returned {resp.status_code}"
                    )
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()

                data = resp.json()
                choice = data["choices"][0]
                content = choice["message"]["content"]
                if not content:
                    # Some auto-routed models (esp. reasoning models under a
                    # tight max_tokens budget) return HTTP 200 with
                    # content=null/"" — the whole token budget went to a
                    # hidden reasoning trace, nothing left for the answer.
                    # Treat it as a provider fault so callers get the
                    # existing "temporarily unavailable" handling instead of
                    # crashing on None downstream.
                    raise ProviderUnavailableError(
                        "Provider returned empty content "
                        f"(model={data.get('model', self._model)})"
                    )
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    model=data.get("model", self._model),
                    provider=self._provider_label,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    latency_ms=latency_ms,
                )
            except (ProviderAuthError, ProviderRateLimitError):
                raise
            except httpx.TimeoutException as exc:
                last_error = ProviderTimeoutError(str(exc))
                if attempt == _MAX_RETRIES:
                    raise ProviderTimeoutError("LLM request timed out") from exc
                time.sleep(2 ** attempt)
            except httpx.HTTPError as exc:
                # Connection-level failures (ConnectError, RemoteProtocolError,
                # etc.) get no response at all, unlike the status-code branch
                # above — retrying instantly against the same transient
                # condition just fails 3x back-to-back. Back off the same way.
                last_error = ProviderUnavailableError(str(exc))
                if attempt == _MAX_RETRIES:
                    raise ProviderUnavailableError(
                        f"LLM request failed: {exc}"
                    ) from exc
                time.sleep(2 ** attempt)

        raise last_error or ProviderUnavailableError("Provider unavailable")
