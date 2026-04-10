"""Approval workflow API — create, review, and manage approval requests."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ApprovalRequest(BaseModel):
    workflow_run_id: str
    action_description: str
    risk_level: str
    requested_by: str
    approvers: list[str]


class ApprovalDecision(BaseModel):
    approved: bool
    comment: str = ""


@router.post("/")
async def create_approval(request: ApprovalRequest) -> dict:
    """Create a new approval request."""
    return {
        "approval_id": "pending",
        "status": "pending",
        "workflow_run_id": request.workflow_run_id,
        "risk_level": request.risk_level,
    }


@router.get("/{approval_id}")
async def get_approval(approval_id: str) -> dict:
    """Get approval request details."""
    return {"approval_id": approval_id, "status": "pending"}


@router.post("/{approval_id}/decide")
async def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict:
    """Submit an approval decision."""
    return {
        "approval_id": approval_id,
        "status": "approved" if decision.approved else "denied",
        "comment": decision.comment,
    }


@router.get("/")
async def list_pending_approvals(status: str = "pending") -> list[dict]:
    """List approval requests by status."""
    return []
