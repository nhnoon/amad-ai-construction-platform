"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part D/E:
Request Protection & Slow-Request Protection.

Pure ASGI middleware — deliberately NOT BaseHTTPMiddleware. Starlette's
BaseHTTPMiddleware reads the full request body into memory (via
`await request.body()`-equivalent machinery) before application code ever
sees it, which would defeat the entire point of a size cap meant to
bound memory use for an oversized request: by the time a
BaseHTTPMiddleware subclass could inspect the size, the damage (an
unbounded buffer) is already done. Wrapping the raw ASGI `receive`
callable instead lets this reject an oversized body mid-stream, before it
is ever fully buffered anywhere — by the application layer OR by this
middleware itself.

Two independent protections, both scoped by content-type (multipart
requests — uploads — get a larger size allowance and a longer time
budget than ordinary JSON/form bodies, matching this app's existing
DOCUMENT_MAX_FILE_SIZE_BYTES / OCR_MAX_FILE_SIZE_BYTES application-layer
caps — see Settings for the exact numbers and the reasoning for each):

1. Body size cap — checked twice: instantly from the Content-Length
   header when present (fast-path rejection before touching the body at
   all), and incrementally as the body streams in (catches a chunked
   request with no Content-Length, or one that understates it).
2. A ceiling on how long it may take to fully RECEIVE the request body
   (protects against slow-loris-style trickling — "very slow uploads" /
   resource exhaustion from a connection held open while dribbling bytes
   in). Deliberately scoped to body reception only, not to how long the
   application then takes to PROCESS an already-fully-received request:
   an earlier version of this middleware wrapped the whole application
   call in one wall-clock timeout and it 408'd the AI Copilot's
   legitimately slow (60-150s+) LLM-backed responses, which already have
   their own considered timeout budgets (HERMES_TIMEOUT_SECONDS and
   friends, app/ai/pipeline.py) — a generic HTTP-layer request-protection
   middleware has no business overriding those. Bounding only the
   receive-loop achieves the actual stated goal (a client that trickles
   bytes in slowly) without that collateral damage, since a normal
   handler that has already fully consumed the body doesn't call
   receive() again while it computes a response.

Every rejection is a plain JSON error with no stack trace and no
internal detail — constructed and sent directly at the raw ASGI level,
never letting an exception reach FastAPI's own error handling.
"""
from __future__ import annotations

import asyncio
import json
import time

from ..config import settings


class _BodyTooLarge(Exception):
    pass


class _BodyTooSlow(Exception):
    pass


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes | None:
    for key, value in headers:
        if key.lower() == name:
            return value
    return None


def _is_multipart(headers: list[tuple[bytes, bytes]]) -> bool:
    content_type = _header(headers, b"content-type")
    return bool(content_type) and content_type.lower().startswith(b"multipart/form-data")


def _content_length(headers: list[tuple[bytes, bytes]]) -> int | None:
    raw = _header(headers, b"content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


async def _send_json_error(send, status_code: int, detail: str, extra_headers: dict[str, str] | None = None) -> None:
    body = json.dumps({"detail": detail}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    for key, value in (extra_headers or {}).items():
        headers.append((key.encode("ascii"), value.encode("ascii")))
    await send({"type": "http.response.start", "status": status_code, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class RequestProtectionMiddleware:
    def __init__(self, app) -> None:
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not settings.REQUEST_PROTECTION_ENABLED:
            await self._app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        is_upload = _is_multipart(headers)
        max_size = settings.REQUEST_MAX_UPLOAD_SIZE_BYTES if is_upload else settings.REQUEST_MAX_BODY_SIZE_BYTES
        timeout_seconds = (
            settings.REQUEST_UPLOAD_TIMEOUT_SECONDS if is_upload else settings.REQUEST_TIMEOUT_SECONDS
        )

        # Fast path: reject instantly from Content-Length, before ever
        # calling into the application.
        content_length = _content_length(headers)
        if content_length is not None and content_length > max_size:
            await _send_json_error(send, 413, "Request body exceeds the maximum allowed size.")
            return

        received = 0
        deadline = time.monotonic() + timeout_seconds

        async def guarded_receive():
            nonlocal received
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _BodyTooSlow()
            try:
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except asyncio.TimeoutError:
                raise _BodyTooSlow()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_size:
                    # Raised INSIDE the awaited receive() call, so it
                    # interrupts whatever Starlette/python-multipart
                    # machinery is mid-read on the app side, rather than
                    # letting more of an oversized body keep streaming in.
                    raise _BodyTooLarge()
            return message

        try:
            await self._app(scope, guarded_receive, send)
        except _BodyTooLarge:
            await _send_json_error(send, 413, "Request body exceeds the maximum allowed size.")
        except _BodyTooSlow:
            await _send_json_error(
                send, 408, "Request body took too long to arrive.",
                extra_headers={"Connection": "close"},
            )
