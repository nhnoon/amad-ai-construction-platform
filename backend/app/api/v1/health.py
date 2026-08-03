from fastapi import APIRouter, Response, status
from ...database import check_db_connection
from ...redis_client import check_redis_connection
from ...config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    """Lightweight process-liveness check — no dependency checks, always
    200 if the process is up enough to handle a request at all. Used by a
    liveness probe that should only restart a truly wedged process, not
    one that's merely degraded (that's what /readyz is for)."""
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/readyz")
def readyz(response: Response):
    """Readiness check for load balancers / orchestrators: an instance
    that fails this should be taken out of rotation.

    RC1 Phase 0 — Security Remediation (Finding 6): this used to always
    return HTTP 200 regardless of dependency health, with "ready" vs
    "degraded" visible only in the JSON body. Most orchestrators
    (Kubernetes readiness probes, autoscalers, load balancer health
    checks) key off the HTTP status code, not body content — so a
    genuinely broken database connection would never actually remove the
    instance from rotation under a standard readiness-probe configuration.

    Dependency policy (explicit, not accidental):
      - database is REQUIRED: nothing in this application functions
        without it, so a failed DB check fails readiness (503).
      - redis is OPTIONAL: as of this sprint nothing in the running
        application actually depends on Redis being reachable — rate
        limiting is in-memory (see app/core/login_security.py and
        app/ai/ratelimit.py), and app/redis_client.py itself already
        treats a connection failure as non-fatal (logs a warning and
        continues with no Redis client). A Redis outage is still reported
        in the response body for visibility, but it never fails
        readiness. Revisit this policy (and this comment) the day a
        feature makes Redis load-bearing.
    """
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()
    ready = db_ok  # redis is optional — see policy note above

    response.status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
