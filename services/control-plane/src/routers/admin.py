"""Admin console API — dashboard, connector status, worker utilization."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard() -> dict:
    """Aggregated admin dashboard: workflow counts, pending approvals, recent audit log."""
    return {
        "workflows": {
            "running": 0,
            "completed_today": 0,
            "failed_today": 0,
        },
        "approvals": {
            "pending": 0,
            "approved_today": 0,
            "denied_today": 0,
        },
        "recent_audit": [],
    }


@router.get("/connectors/status")
async def get_connector_status() -> list[dict]:
    """Connector health overview."""
    return [
        {"name": "entra_id", "status": "healthy", "last_check": None},
        {"name": "servicenow", "status": "healthy", "last_check": None},
    ]


@router.get("/workers/utilization")
async def get_worker_utilization() -> dict:
    """Worker pool utilization metrics."""
    return {
        "total_workers": 0,
        "active_workers": 0,
        "queued_tasks": 0,
        "utilization_pct": 0.0,
    }


@router.get("/audit")
async def get_audit_log(limit: int = 50, offset: int = 0) -> dict:
    """Paginated audit log viewer with filtering support."""
    return {
        "entries": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }
