import redis
from .config import settings
import logging

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis_client() -> "redis.Redis | None":
    global _redis_client
    if _redis_client is None:
        try:
            client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            _redis_client = client
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Continuing without Redis.")
            _redis_client = None
    return _redis_client


def check_redis_connection() -> bool:
    try:
        client = get_redis_client()
        if client is None:
            return False
        client.ping()
        return True
    except Exception:
        return False
