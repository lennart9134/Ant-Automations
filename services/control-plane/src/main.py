"""Control plane service — admin console, tenant config, RBAC, and safety layer."""

from fastapi import FastAPI

from .routers import admin, approvals
from .rbac.middleware import RBACMiddleware

app = FastAPI(title="Ant Automations Control Plane", version="0.1.0")

app.add_middleware(RBACMiddleware)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "control-plane"}
