"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part D/E tests:
request size limits, multipart safety, and slow-request protection.

Exercises RequestProtectionMiddleware in isolation, wrapping a minimal
throwaway echo ASGI app — same "build a small standalone app rather than
depend on a real route" precedent already used by
tests/test_docs_production_gating.py. This keeps these tests independent
of the Documents domain (Sprint 3 must not modify or depend on its
internals) while still exercising the real middleware class unmodified.

Note: TestClient is used WITHOUT its `with ... as c:` context manager
here — entering that context drives Starlette's lifespan protocol
(startup/shutdown events), which these bare middleware-wrapped apps don't
implement (only real FastAPI apps like app.main.app do). Without `with`,
TestClient just makes plain HTTP-protocol requests, which is all these
tests need.
"""
import asyncio
import json

from starlette.testclient import TestClient

from app.config import settings
from app.core.request_protection import RequestProtectionMiddleware


async def _echo_app(scope, receive, send):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    response = str(len(body)).encode("ascii")
    await send({
        "type": "http.response.start", "status": 200,
        "headers": [(b"content-type", b"text/plain"), (b"content-length", str(len(response)).encode())],
    })
    await send({"type": "http.response.body", "body": response})


def _make_client() -> TestClient:
    return TestClient(RequestProtectionMiddleware(_echo_app))


def test_normal_sized_request_passes_through():
    c = _make_client()
    r = c.post("/anything", content=b"hello world")
    assert r.status_code == 200
    assert r.text == "11"


def test_oversized_content_length_rejected_before_body_read(monkeypatch):
    """Fast path: Content-Length alone is enough to reject — proven by
    using a body the server would otherwise have to fully receive to
    even notice via the streaming counter."""
    monkeypatch.setattr(settings, "REQUEST_MAX_BODY_SIZE_BYTES", 100)
    c = _make_client()
    r = c.post("/anything", content=b"x" * 1000)
    assert r.status_code == 413
    assert r.json() == {"detail": "Request body exceeds the maximum allowed size."}


def test_oversized_chunked_body_rejected_mid_stream(monkeypatch):
    """No Content-Length header (chunked transfer) — must still be
    caught by the incremental byte-counting guard, not just the
    Content-Length fast path."""
    monkeypatch.setattr(settings, "REQUEST_MAX_BODY_SIZE_BYTES", 100)

    def chunk_generator():
        for _ in range(20):
            yield b"x" * 50  # 20 * 50 = 1000 bytes total, well over the 100-byte cap

    c = _make_client()
    r = c.post("/anything", content=chunk_generator())
    assert r.status_code == 413


def test_upload_scope_gets_a_larger_size_allowance(monkeypatch):
    """A multipart body between the ordinary cap and the upload cap must
    be accepted, not rejected — proves the two limits are genuinely
    independent (Content-Type-based classification), matching Part D's
    "no regression on uploads" requirement."""
    monkeypatch.setattr(settings, "REQUEST_MAX_BODY_SIZE_BYTES", 100)
    monkeypatch.setattr(settings, "REQUEST_MAX_UPLOAD_SIZE_BYTES", 10_000)
    c = _make_client()
    r = c.post("/anything", files={"file": ("big.bin", b"x" * 5000, "application/octet-stream")})
    assert r.status_code == 200


def test_upload_scope_still_bounded_by_its_own_cap(monkeypatch):
    monkeypatch.setattr(settings, "REQUEST_MAX_UPLOAD_SIZE_BYTES", 100)
    c = _make_client()
    r = c.post("/anything", files={"file": ("big.bin", b"x" * 5000, "application/octet-stream")})
    assert r.status_code == 413


def test_request_protection_disabled_via_settings(monkeypatch):
    monkeypatch.setattr(settings, "REQUEST_PROTECTION_ENABLED", False)
    monkeypatch.setattr(settings, "REQUEST_MAX_BODY_SIZE_BYTES", 10)
    c = _make_client()
    r = c.post("/anything", content=b"x" * 1000)
    assert r.status_code == 200


async def test_slow_body_reception_times_out(monkeypatch):
    """Part E: slow-loris protection — a body that trickles in too slowly
    must be aborted with a graceful error. Deliberately scoped to BODY
    RECEPTION only, not to how long the application then takes to process
    an already-fully-received request (see request_protection.py's module
    docstring — an earlier version bounded the whole request and broke
    the AI Copilot's legitimately slow, 60-150s+ LLM-backed responses).
    Drives the ASGI interface directly (not via TestClient/httpx, which
    doesn't offer a way to insert a real async delay mid-body) so the
    slow arrival can be simulated precisely."""
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT_SECONDS", 1)

    scope = {"type": "http", "method": "POST", "headers": []}

    async def slow_receive():
        await asyncio.sleep(2)  # slower than the 1s body-reception ceiling
        return {"type": "http.request", "body": b"data", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    await RequestProtectionMiddleware(_echo_app)(scope, slow_receive, send)

    start = next(m for m in sent if m["type"] == "http.response.start")
    body = next(m for m in sent if m["type"] == "http.response.body")
    assert start["status"] == 408
    assert json.loads(body["body"]) == {"detail": "Request body took too long to arrive."}


async def test_a_fully_processed_request_is_never_timed_out_by_slow_handling(monkeypatch):
    """The critical regression check: once the body is FULLY received
    (quickly), the application may take as long as it needs to process
    it — RequestProtectionMiddleware must never intervene again, since it
    has no visibility into (or business overriding) the application's own
    processing-time budgets."""
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT_SECONDS", 1)

    async def slow_handler_app(scope, receive, send):
        await receive()  # body arrives instantly
        await asyncio.sleep(3)  # handler itself is slow — e.g. an LLM call
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"finally done"})

    c = TestClient(RequestProtectionMiddleware(slow_handler_app))
    r = c.get("/anything")
    assert r.status_code == 200
    assert r.text == "finally done"


async def test_upload_scope_gets_a_longer_body_reception_allowance(monkeypatch):
    """A legitimately slow (but not abusive) upload must not be timed out
    at the ordinary request's body-reception ceiling."""
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(settings, "REQUEST_UPLOAD_TIMEOUT_SECONDS", 5)

    scope = {"type": "http", "method": "POST", "headers": [(b"content-type", b"multipart/form-data; boundary=x")]}

    async def slow_upload_receive():
        await asyncio.sleep(2)  # slower than the ordinary 1s ceiling, within the 5s upload one
        return {"type": "http.request", "body": b"data", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    await RequestProtectionMiddleware(_echo_app)(scope, slow_upload_receive, send)

    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 200
