"""RBAC middleware — role-based access control for the control plane API.

Roles:
- platform_admin: full access to all tenants and settings
- tenant_admin: full access within their tenant
- operator: read + execute workflows, approve actions
- viewer: read-only access to dashboards and audit log
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# JWT configuration — set via environment variables in production.
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.PLATFORM_ADMIN: {"*"},
    Role.TENANT_ADMIN: {
        "dashboard:read",
        "audit:read",
        "connectors:read",
        "connectors:configure",
        "workflows:read",
        "workflows:execute",
        "approvals:read",
        "approvals:decide",
        "tenants:read",
        "tenants:configure",
        "users:read",
        "users:manage",
    },
    Role.OPERATOR: {
        "dashboard:read",
        "audit:read",
        "connectors:read",
        "workflows:read",
        "workflows:execute",
        "approvals:read",
        "approvals:decide",
    },
    Role.VIEWER: {
        "dashboard:read",
        "audit:read",
        "connectors:read",
        "workflows:read",
        "approvals:read",
    },
}

# Paths that require specific permissions (prefix match).
PATH_PERMISSIONS: list[tuple[str, str, str]] = [
    # (path_prefix, http_method, required_permission)
    ("/api/v1/admin/dashboard", "GET", "dashboard:read"),
    ("/api/v1/admin/connectors", "GET", "connectors:read"),
    ("/api/v1/admin/workers", "GET", "dashboard:read"),
    ("/api/v1/admin/audit", "GET", "audit:read"),
    ("/api/v1/approvals", "GET", "approvals:read"),
    ("/api/v1/approvals", "POST", "approvals:decide"),
]


@dataclass
class UserContext:
    user_id: str
    tenant_id: str
    role: Role
    permissions: set[str]


def check_permission(user: UserContext, required: str) -> bool:
    if "*" in user.permissions:
        return True
    return required in user.permissions


def _resolve_required_permission(path: str, method: str) -> str | None:
    """Return the permission required for a given path and method, or None."""
    for prefix, m, perm in PATH_PERMISSIONS:
        if path.startswith(prefix) and method.upper() == m:
            return perm
    return None


class RBACMiddleware(BaseHTTPMiddleware):
    """Extracts user context from JWT and enforces role-based access.

    When JWT_SECRET is not configured (empty string), the middleware operates
    in development mode: all requests are allowed through with a default
    viewer context and a warning is logged on first request.
    """

    _dev_mode_warned: bool = False

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip health checks
        if request.url.path == "/healthz":
            return await call_next(request)

        # --- Development mode: no JWT_SECRET configured ---
        if not JWT_SECRET:
            if not RBACMiddleware._dev_mode_warned:
                logger.warning(
                    "JWT_SECRET is not set — RBAC middleware running in DEVELOPMENT mode. "
                    "All requests are granted viewer permissions. "
                    "Set JWT_SECRET to enable authentication."
                )
                RBACMiddleware._dev_mode_warned = True

            request.state.user = UserContext(
                user_id="dev-user",
                tenant_id="default",
                role=Role.VIEWER,
                permissions=ROLE_PERMISSIONS[Role.VIEWER],
            )
            return await call_next(request)

        # --- Production mode: decode JWT from Authorization header ---
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid token: {exc}"},
            )

        # Extract claims — expected: sub, tenant_id, role
        user_id = payload.get("sub", "")
        tenant_id = payload.get("tenant_id", "")
        role_value = payload.get("role", "")

        try:
            role = Role(role_value)
        except ValueError:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Unknown role: {role_value}"},
            )

        user = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            permissions=ROLE_PERMISSIONS[role],
        )

        # Enforce permission for the requested path
        required = _resolve_required_permission(request.url.path, request.method)
        if required and not check_permission(user, required):
            return JSONResponse(
                status_code=403,
                content={"detail": f"Insufficient permissions, requires: {required}"},
            )

        request.state.user = user
        return await call_next(request)
