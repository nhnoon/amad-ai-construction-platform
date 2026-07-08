from fastapi import APIRouter
from ...database import check_db_connection
from ...redis_client import check_redis_connection
from ...config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/readyz")
def readyz():
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()
    all_ok = db_ok

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
