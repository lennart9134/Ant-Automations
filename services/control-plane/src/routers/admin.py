"""Admin console API — dashboard, connector status, worker utilization, audit log."""

from fastapi import APIRouter, Request

from ..safety.audit import AuditTrailService

router = APIRouter()


def _get_audit(request: Request) -> AuditTrailService:
    return request.app.state.audit_service


@router.get("/dashboard")
async def get_dashboard(request: Request) -> dict:
    """Aggregated admin dashboard: workflow counts, pending approvals, recent audit log."""
    audit = _get_audit(request)
    approval_svc = request.app.state.approval_service
    recent = await audit.query(limit=10)
    pending_count = sum(1 for r in approval_svc._requests.values() if r.state.value == "pending")
    return {
        "workflows": {
            "running": 0,
            "completed_today": 0,
            "failed_today": 0,
        },
        "approvals": {
            "pending": pending_count,
            "approved_today": 0,
            "denied_today": 0,
        },
        "recent_audit": [{"id": e.id, "event_type": e.event_type.value, "action": e.action} for e in recent],
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
async def get_audit_log(limit: int = 50, offset: int = 0, request: Request = None) -> dict:
    """Paginated audit log viewer, backed by AuditTrailService."""
    audit = _get_audit(request)
    all_events = await audit.query(limit=limit + offset)
    page = all_events[offset : offset + limit]
    return {
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "event_type": e.event_type.value,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
            }
            for e in page
        ],
        "total": len(audit._events),
        "limit": limit,
        "offset": offset,
    }
