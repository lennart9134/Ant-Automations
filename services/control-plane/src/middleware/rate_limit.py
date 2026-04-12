"""Rate-limiting middleware using Redis sliding-window counters.

Enterprise requirement (Business Plan §11.1): protect API endpoints from
abuse and enforce per-tenant usage quotas. Uses Redis for distributed
state so rate limits work across multiple service replicas.

Configuration via environment variables:
- RATE_LIMIT_RPM: requests per minute per client (default 120)
- RATE_LIMIT_ENABLED: set to "false" to disable (default "true")
"""

from __future__ import annotations

import logging
import os
import time

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "120"))
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Paths exempt from rate limiting
EXEMPT_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}


def _client_key(request: Request) -> str:
    """Derive a rate-limit key from the request.

    Priority: tenant_id from JWT > X-Forwarded-For > client host.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "tenant_id"):
        return f"rl:{user.tenant_id}:{user.user_id}"
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return f"rl:ip:{forwarded.split(',')[0].strip()}"
    host = request.client.host if request.client else "unknown"
    return f"rl:ip:{host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by Redis.

    Falls back to pass-through if Redis is unavailable (graceful degradation).
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if not RATE_LIMIT_ENABLED or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        key = _client_key(request)
        window = 60  # seconds

        try:
            now = time.time()
            window_start = now - window

            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window + 1)
            results = await pipe.execute()

            request_count = results[2]
        except Exception:
            logger.debug("Rate limiter Redis error — allowing request", exc_info=True)
            return await call_next(request)

        if request_count > RATE_LIMIT_RPM:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(RATE_LIMIT_RPM),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_RPM)
        response.headers["X-RateLimit-Remaining"] = str(max(0, RATE_LIMIT_RPM - request_count))
        return response
