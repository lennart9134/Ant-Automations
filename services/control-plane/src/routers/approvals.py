"""Approval workflow API — create, review, and manage approval requests."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..safety.approvals import ApprovalChainService, RiskLevel

router = APIRouter()


class CreateApprovalRequest(BaseModel):
    workflow_run_id: str
    action_description: str
    risk_level: str
    requested_by: str
    approvers: list[str]


class ApprovalDecision(BaseModel):
    approved: bool
    comment: str = ""


def _get_service(request: Request) -> ApprovalChainService:
    return request.app.state.approval_service


@router.post("/")
async def create_approval(body: CreateApprovalRequest, request: Request) -> dict:
    """Create a new approval request routed through the ApprovalChainService."""
    svc = _get_service(request)
    req = svc.create_request(
        workflow_run_id=body.workflow_run_id,
        action_description=body.action_description,
        risk_level=RiskLevel(body.risk_level),
        approvers=body.approvers,
    )
    return {
        "approval_id": req.id,
        "status": req.state.value,
        "workflow_run_id": req.workflow_run_id,
        "risk_level": req.risk_level.value,
    }


@router.get("/{approval_id}")
async def get_approval(approval_id: str, request: Request) -> dict:
    """Get approval request details."""
    svc = _get_service(request)
    req = svc.get(approval_id)
    if req is None:
        return {"detail": "Not found", "approval_id": approval_id}
    return {
        "approval_id": req.id,
        "status": req.state.value,
        "steps": [
            {
                "approver_id": s.approver_id,
                "decided": s.decided,
                "decision": s.decision.value,
            }
            for s in req.steps
        ],
    }


@router.post("/{approval_id}/decide")
async def decide_approval(approval_id: str, decision: ApprovalDecision, request: Request) -> dict:
    """Submit an approval decision."""
    svc = _get_service(request)
    user = request.state.user
    req = svc.decide(
        request_id=approval_id,
        approver_id=user.user_id,
        approved=decision.approved,
        comment=decision.comment,
    )
    return {
        "approval_id": req.id,
        "status": req.state.value,
        "comment": decision.comment,
    }


@router.get("/")
async def list_pending_approvals(status: str = "pending", request: Request = None) -> list[dict]:
    """List approval requests by status."""
    svc = _get_service(request)
    return [
        {
            "approval_id": req.id,
            "status": req.state.value,
            "action_description": req.action_description,
            "risk_level": req.risk_level.value,
        }
        for req in svc._requests.values()
        if req.state.value == status
    ]
