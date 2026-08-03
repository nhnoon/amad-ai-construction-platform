#!/usr/bin/env python
import os
import sys
import uvicorn

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(__file__))

# RC1 Phase 0 — Security Remediation (Finding 2): SESSION_SECRET must come
# from a real environment value (a local .env file, or a platform secret in
# production) — no hardcoded fallback here. A missing/empty SESSION_SECRET
# used to silently default to the well-known literal "dev-secret" via
# os.environ.setdefault(), which would let anyone forge a valid JWT for any
# deployment launched through this script without SESSION_SECRET explicitly
# set. app.config.Settings already fails fast (raises before the app can
# serve any request) if SESSION_SECRET is missing or empty — importing it
# here, before uvicorn starts, surfaces that failure immediately and
# deterministically rather than depending on uvicorn's own import timing.
# For local development, generate a persisted secret once (so restarting
# the server doesn't invalidate everyone's active session) via:
#   python -c "import secrets; print(secrets.token_hex(32))"
# and put it in backend/.env as SESSION_SECRET=... (see .env.example).
from app.config import settings as _settings  # noqa: E402,F401  (import triggers fail-fast validation)

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        reload=False,
        log_level='info'
    )
