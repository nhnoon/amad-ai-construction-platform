"""Hermes Agent provider adapter.

Integration method (confirmed by inspecting the locally installed Hermes
Agent v0.18.2, see ``hermes --help`` / ``hermes serve --help`` /
``hermes proxy --help``):

  * Hermes exposes NO OpenAI-compatible chat-completions HTTP endpoint of its
    own. ``hermes serve`` is a JSON-RPC/WebSocket gateway for the desktop
    app, not a completions API. ``hermes proxy`` only forwards to
    OAuth-authenticated cloud providers (e.g. Nous Portal), not to a local
    Ollama model.
  * The officially supported non-interactive integration point is the CLI's
    oneshot mode: ``hermes -z PROMPT`` — documented by Hermes itself as
    "Intended for scripts / pipes", auto-bypasses approvals, and prints only
    the final response text to stdout.
  * Locally, Hermes is configured to serve qwen2.5:3b through Ollama's own
    OpenAI-compatible endpoint (``http://127.0.0.1:11434/v1``, Hermes
    provider name ``ollama-launch`` — see ``hermes config path``).

This adapter therefore shells out to ``hermes -p <profile> -z <prompt>`` as a
subprocess (argument list, never ``shell=True``, never string-concatenated).
The ``<profile>`` is a dedicated, isolated Hermes profile ("amad" by
default, see ``hermes profile create amad --clone``) with all toolsets and
cross-session memory disabled in its config.yaml, so this call can only ever
produce text — it has no shell, browser, file, or database access. Grounding
evidence and instructions arrive solely via the prompt text built by
app/ai/pipeline.py; Hermes never touches the database directly.

Known limitation: Hermes Agent refuses to start against any model reporting
a context window under its hardcoded 64K-token minimum. Ollama reports
qwen2.5:3b's window as 32,768 tokens, so the amad profile sets
``model.context_length: 64000`` purely to satisfy that startup gate — this
does NOT raise the real context Ollama serves (see the comment in that
profile's config.yaml). Keep combined system+evidence+user prompts well
under the real ~32K-token ceiling.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from .base import (
    LLMRequest,
    LLMResponse,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Combined system+evidence+user prompt is passed as a single argv element to
# a Windows subprocess (no shell involved, so the ~32K-char CreateProcess
# command-line ceiling applies, not cmd.exe's smaller 8191 limit). Capping
# well below that also keeps us under Hermes/Ollama's real ~32K-token
# context window (see module docstring).
_MAX_PROMPT_CHARS = 20000
_TRUNCATION_NOTICE = "\n...(evidence truncated to fit the model's context window)"

_AUTH_MARKERS = ("unauthorized", "authentication failed", "invalid api key", "401")
_RATE_LIMIT_MARKERS = ("rate limit", "429", "too many requests")
_UNAVAILABLE_MARKERS = (
    "connection refused",
    "connect error",
    "could not connect",
    "failed to establish a new connection",
    "econnrefused",
    "connection error",
    "no such host",
)


def _truncate_prompt(prompt: str) -> str:
    if len(prompt) <= _MAX_PROMPT_CHARS:
        return prompt
    keep = _MAX_PROMPT_CHARS - len(_TRUNCATION_NOTICE)
    return prompt[:keep] + _TRUNCATION_NOTICE


class HermesProvider:
    """Calls a local Hermes Agent profile via non-interactive CLI oneshot mode."""

    def __init__(
        self,
        model: str,
        hermes_bin: Optional[str] = None,
        profile: str = "amad",
        hermes_provider: str = "ollama-launch",
        timeout_seconds: int = 120,
    ) -> None:
        self._model = model
        self._profile = profile
        self._hermes_provider = hermes_provider
        self._timeout_seconds = timeout_seconds
        self._hermes_bin = hermes_bin or shutil.which("hermes")

    @property
    def provider_name(self) -> str:
        return "hermes"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._hermes_bin) and Path(self._hermes_bin).is_file()

    def generate(self, request: LLMRequest) -> LLMResponse:
        # TEMPORARY instrumentation — remove once Hermes wiring is verified.
        logger.info(
            "Entering HermesProvider.generate() model=%s profile=%s hermes_provider=%s",
            self._model, self._profile, self._hermes_provider,
        )
        if not self.is_available():
            raise ProviderUnavailableError(
                "Hermes executable not found on PATH; set HERMES_BIN or install Hermes Agent."
            )

        prompt = _truncate_prompt(
            "SYSTEM INSTRUCTIONS (authoritative for this turn):\n"
            f"{request.system_prompt}\n\n"
            "USER QUESTION:\n"
            f"{request.user_prompt}"
        )

        usage_path = Path(tempfile.gettempdir()) / f"hermes_usage_{uuid.uuid4().hex}.json"
        args = [
            self._hermes_bin,
            "-p", self._profile,
            "-z", prompt,
            "-m", self._model,
            "--provider", self._hermes_provider,
            "--usage-file", str(usage_path),
        ]

        # TEMPORARY instrumentation — never logs the prompt/evidence itself.
        logger.info(
            "Hermes command execution: %s -p %s -z <prompt len=%d, redacted> -m %s --provider %s (timeout=%ss)",
            self._hermes_bin, self._profile, len(prompt), self._model,
            self._hermes_provider, self._timeout_seconds,
        )

        start = time.monotonic()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                cwd=tempfile.gettempdir(),
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderTimeoutError(
                f"Hermes agent timed out after {self._timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise ProviderUnavailableError(f"Failed to launch Hermes agent: {exc}") from exc
        latency_ms = (time.monotonic() - start) * 1000

        # TEMPORARY instrumentation.
        logger.info(
            "Hermes response received: returncode=%d stdout_len=%d latency_ms=%.1f",
            result.returncode, len(result.stdout or ""), latency_ms,
        )

        usage = self._read_and_delete_usage_file(usage_path)

        if result.returncode != 0:
            raise self._map_error(result.returncode, result.stderr or "")

        content = (result.stdout or "").strip()
        if not content:
            raise ProviderUnavailableError("Hermes agent returned an empty response")

        response_model = (usage or {}).get("model") or self._model

        # TEMPORARY instrumentation.
        logger.info(
            "HermesProvider.generate() complete: provider=hermes model=%s latency_ms=%.1f",
            response_model, latency_ms,
        )

        return LLMResponse(
            content=content,
            model=response_model,
            provider="hermes",
            prompt_tokens=(usage or {}).get("input_tokens"),
            completion_tokens=(usage or {}).get("output_tokens"),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _read_and_delete_usage_file(path: Path) -> Optional[dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        finally:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        return data

    @staticmethod
    def _map_error(returncode: int, stderr: str) -> Exception:
        lowered = stderr.lower()
        # Never log the prompt/evidence — only Hermes's own short error text,
        # truncated defensively in case it ever echoes something unexpected.
        safe_detail = stderr.strip()[:300]
        logger.warning("Hermes agent exited %d: %s", returncode, safe_detail)

        if any(marker in lowered for marker in _AUTH_MARKERS):
            return ProviderAuthError(f"Hermes agent authentication failed: {safe_detail}")
        if any(marker in lowered for marker in _RATE_LIMIT_MARKERS):
            return ProviderRateLimitError(f"Hermes agent rate limited: {safe_detail}")
        if "timed out" in lowered or "timeout" in lowered:
            return ProviderTimeoutError(f"Hermes agent timed out: {safe_detail}")
        if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
            return ProviderUnavailableError(f"Hermes agent unavailable: {safe_detail}")
        return ProviderUnavailableError(
            f"Hermes agent failed (exit {returncode}): {safe_detail}"
        )
