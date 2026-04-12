"""Tenant isolation middleware.

Enterprise requirement (Business Plan §6.3, §11.1): ensure that every API
request is scoped to a single tenant. Data from tenant A must never leak
into responses for tenant B.

The middleware:
1. Extracts tenant_id from the authenticated user context (set by RBAC middleware).
2. Attaches it to request.state for downstream handlers.
3. Rejects requests where tenant_id is missing in production mode.

This is not the full data-layer isolation (that belongs in the DB/query layer),
but it provides the request-level boundary that all downstream code can trust.
"""

from __future__ import annotations

import logging
import os

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

TENANT_ISOLATION_ENABLED = os.getenv("TENANT_ISOLATION_ENABLED", "true").lower() == "true"

EXEMPT_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Ensures every request is scoped to a valid tenant.

    Must be placed AFTER the RBAC middleware in the middleware stack,
    since it reads user context set by RBAC.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        if not TENANT_ISOLATION_ENABLED:
            return await call_next(request)

        user = getattr(request.state, "user", None)

        if user is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        tenant_id = getattr(user, "tenant_id", "")
        if not tenant_id:
            logger.warning("Request from user %s has no tenant_id", getattr(user, "user_id", "?"))
            return JSONResponse(
                status_code=403,
                content={"detail": "Tenant context required. Contact your administrator."},
            )

        # Set tenant on request state for downstream handlers
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        # Include tenant ID in response headers for debugging/audit
        response.headers["X-Tenant-ID"] = tenant_id
        return response
