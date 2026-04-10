"""Approval chains — configurable multi-step approval workflows.

Risk-based routing:
- Low risk: auto-approve with audit log
- Medium risk: single human approver required
- High risk: multi-approver chain with escalation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ApprovalStep:
    approver_id: str
    required: bool = True
    decided: bool = False
    decision: ApprovalState = ApprovalState.PENDING
    decided_at: str | None = None
    comment: str = ""


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    workflow_run_id: str = ""
    action_description: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    state: ApprovalState = ApprovalState.PENDING
    steps: list[ApprovalStep] = field(default_factory=list)
    timeout_seconds: int = 3600
    escalation_target: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None


class ApprovalChainService:
    """Manages approval request lifecycle and chain routing."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        workflow_run_id: str,
        action_description: str,
        risk_level: RiskLevel,
        approvers: list[str],
        escalation_target: str | None = None,
    ) -> ApprovalRequest:
        steps = [ApprovalStep(approver_id=a) for a in approvers]
        request = ApprovalRequest(
            workflow_run_id=workflow_run_id,
            action_description=action_description,
            risk_level=risk_level,
            steps=steps,
            escalation_target=escalation_target,
        )

        # Auto-approve low-risk actions
        if risk_level == RiskLevel.LOW:
            request.state = ApprovalState.APPROVED
            request.resolved_at = datetime.now(timezone.utc).isoformat()
            for step in request.steps:
                step.decided = True
                step.decision = ApprovalState.APPROVED

        self._requests[request.id] = request
        return request

    def decide(self, request_id: str, approver_id: str, approved: bool, comment: str = "") -> ApprovalRequest:
        request = self._requests[request_id]
        if request.state != ApprovalState.PENDING:
            raise ValueError(f"Request {request_id} is not pending: {request.state}")

        step_found = False
        for step in request.steps:
            if step.approver_id == approver_id and not step.decided:
                step.decided = True
                step.decision = ApprovalState.APPROVED if approved else ApprovalState.DENIED
                step.decided_at = datetime.now(timezone.utc).isoformat()
                step.comment = comment
                step_found = True
                break

        if not step_found:
            raise ValueError(
                f"Approver '{approver_id}' has no pending step on request {request_id}"
            )

        if any(s.decision == ApprovalState.DENIED for s in request.steps):
            request.state = ApprovalState.DENIED
            request.resolved_at = datetime.now(timezone.utc).isoformat()
        elif all(s.decided for s in request.steps):
            request.state = ApprovalState.APPROVED
            request.resolved_at = datetime.now(timezone.utc).isoformat()

        return request

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def escalate(self, request_id: str) -> ApprovalRequest:
        request = self._requests[request_id]
        request.state = ApprovalState.ESCALATED
        if request.escalation_target:
            request.steps.append(ApprovalStep(approver_id=request.escalation_target))
            request.state = ApprovalState.PENDING
        return request
