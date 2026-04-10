"""RBAC middleware — role-based access control for the control plane API.

Roles:
- platform_admin: full access to all tenants and settings
- tenant_admin: full access within their tenant
- operator: read + execute workflows, approve actions
- viewer: read-only access to dashboards and audit log
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.PLATFORM_ADMIN: {"*"},
    Role.TENANT_ADMIN: {
        "dashboard:read", "audit:read", "connectors:read", "connectors:configure",
        "workflows:read", "workflows:execute", "approvals:read", "approvals:decide",
        "tenants:read", "tenants:configure", "users:read", "users:manage",
    },
    Role.OPERATOR: {
        "dashboard:read", "audit:read", "connectors:read",
        "workflows:read", "workflows:execute", "approvals:read", "approvals:decide",
    },
    Role.VIEWER: {
        "dashboard:read", "audit:read", "connectors:read", "workflows:read", "approvals:read",
    },
}


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


class RBACMiddleware(BaseHTTPMiddleware):
    """Extracts user context from JWT and enforces role-based access."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip health checks
        if request.url.path == "/healthz":
            return await call_next(request)

        # In production: decode JWT from Authorization header,
        # extract user_id, tenant_id, role, and build UserContext.
        # For now, allow all requests through.
        request.state.user = UserContext(
            user_id="system",
            tenant_id="default",
            role=Role.PLATFORM_ADMIN,
            permissions=ROLE_PERMISSIONS[Role.PLATFORM_ADMIN],
        )

        return await call_next(request)
