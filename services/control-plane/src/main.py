"""Control plane service — admin console, tenant config, RBAC, and safety layer."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .routers import admin, approvals
from .rbac.middleware import RBACMiddleware
from .safety.approvals import ApprovalChainService
from .safety.audit import AuditTrailService
from .safety.policy import create_default_policies
from .tenants.service import TenantService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared domain services on startup."""
    app.state.approval_service = ApprovalChainService()
    app.state.audit_service = AuditTrailService()
    app.state.policy_engine = create_default_policies()
    app.state.tenant_service = TenantService()
    yield


app = FastAPI(title="Ant Automations Control Plane", version="0.1.0", lifespan=lifespan)

app.add_middleware(RBACMiddleware)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "control-plane"}
