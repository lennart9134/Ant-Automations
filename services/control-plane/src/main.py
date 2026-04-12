"""Control plane service — admin console, tenant config, RBAC, and safety layer."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .db.pool import DatabasePool
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.tenant import TenantIsolationMiddleware
from .rbac.middleware import RBACMiddleware
from .routers import admin, approvals
from .safety.approvals import ApprovalChainService
from .safety.audit import AuditTrailService
from .safety.policy import create_default_policies
from .tenants.service import TenantService

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared domain services and infrastructure on startup."""
    # Database
    db = DatabasePool()
    await db.connect()
    app.state.db = db

    # Redis
    if REDIS_URL:
        app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info("Redis connected (%s)", REDIS_URL)
    else:
        app.state.redis = None
        logger.warning("REDIS_URL not set — running without Redis")

    # Domain services
    app.state.approval_service = ApprovalChainService()
    app.state.audit_service = AuditTrailService()
    app.state.policy_engine = create_default_policies()
    app.state.tenant_service = TenantService()

    yield

    # Shutdown
    if app.state.redis:
        await app.state.redis.aclose()
    await db.close()


app = FastAPI(
    title="Ant Automations Control Plane",
    version="0.1.0",
    description=(
        "Enterprise automation platform control plane — admin console, tenant management, "
        "RBAC, approval chains, policy engine, and audit trail."
    ),
    lifespan=lifespan,
)

# --- Middleware (order matters: outermost runs first) ---
# CORS must be outermost to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Rate limiting runs before auth to protect against brute-force
app.add_middleware(RateLimitMiddleware)
# RBAC authenticates and sets user context
app.add_middleware(RBACMiddleware)
# Tenant isolation ensures every request is scoped (reads RBAC context)
app.add_middleware(TenantIsolationMiddleware)

app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])


@app.get("/healthz")
async def health() -> dict:
    db_ok = await app.state.db.healthcheck() if app.state.db.connected else None
    redis_ok = None
    if app.state.redis:
        try:
            await app.state.redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

    healthy = (db_ok is not False) and (redis_ok is not False)
    return {
        "status": "ok" if healthy else "degraded",
        "service": "control-plane",
        "checks": {"postgres": db_ok, "redis": redis_ok},
    }
