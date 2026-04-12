"""Approval chains — configurable multi-step approval workflows.

Persists requests and steps to Postgres when a database pool is provided.
Falls back to in-memory storage for local development and tests.

Risk-based routing:
- Low risk: auto-approve with audit log
- Medium risk: single human approver required
- High risk: multi-approver chain with escalation
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..db.pool import DatabasePool

logger = logging.getLogger(__name__)


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


class RiskLevel(StrEnum):
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
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved_at: str | None = None


class ApprovalChainService:
    """Manages approval request lifecycle and chain routing.

    When a DatabasePool is attached via ``set_db()``, requests and their
    steps are persisted to the ``approval_requests`` / ``approval_steps``
    tables (schema in migration 001).
    """

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._db: DatabasePool | None = None

    def set_db(self, db: DatabasePool) -> None:
        self._db = db

    async def create_request(
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
            request.resolved_at = datetime.now(UTC).isoformat()
            for step in request.steps:
                step.decided = True
                step.decision = ApprovalState.APPROVED

        self._requests[request.id] = request
        await self._persist_request(request)
        return request

    async def decide(self, request_id: str, approver_id: str, approved: bool, comment: str = "") -> ApprovalRequest:
        request = await self.get(request_id)
        if request is None:
            raise KeyError(f"Approval request {request_id} not found")
        if request.state != ApprovalState.PENDING:
            raise ValueError(f"Request {request_id} is not pending: {request.state}")

        step_found = False
        for step in request.steps:
            if step.approver_id == approver_id and not step.decided:
                step.decided = True
                step.decision = ApprovalState.APPROVED if approved else ApprovalState.DENIED
                step.decided_at = datetime.now(UTC).isoformat()
                step.comment = comment
                step_found = True
                break

        if not step_found:
            raise ValueError(f"Approver '{approver_id}' has no pending step on request {request_id}")

        if any(s.decision == ApprovalState.DENIED for s in request.steps):
            request.state = ApprovalState.DENIED
            request.resolved_at = datetime.now(UTC).isoformat()
        elif all(s.decided for s in request.steps):
            request.state = ApprovalState.APPROVED
            request.resolved_at = datetime.now(UTC).isoformat()

        self._requests[request.id] = request
        await self._persist_request(request)
        return request

    async def get(self, request_id: str) -> ApprovalRequest | None:
        if request_id in self._requests:
            return self._requests[request_id]
        if self._db and self._db.connected:
            return await self._load_request(request_id)
        return None

    async def escalate(self, request_id: str) -> ApprovalRequest:
        request = await self.get(request_id)
        if request is None:
            raise KeyError(f"Approval request {request_id} not found")
        request.state = ApprovalState.ESCALATED
        if request.escalation_target:
            request.steps.append(ApprovalStep(approver_id=request.escalation_target))
            request.state = ApprovalState.PENDING
        self._requests[request.id] = request
        await self._persist_request(request)
        return request

    # -- Postgres persistence --------------------------------------------------

    async def _persist_request(self, request: ApprovalRequest) -> None:
        if not self._db or not self._db.connected:
            return
        try:
            await self._db.execute(
                """INSERT INTO approval_requests
                   (id, correlation_id, workflow_run_id, action_description,
                    risk_level, state, timeout_seconds, escalation_target,
                    created_at, resolved_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                   ON CONFLICT (id) DO UPDATE SET
                     state = EXCLUDED.state,
                     resolved_at = EXCLUDED.resolved_at""",
                request.id,
                request.correlation_id,
                request.workflow_run_id,
                request.action_description,
                request.risk_level.value,
                request.state.value,
                request.timeout_seconds,
                request.escalation_target,
                request.created_at,
                request.resolved_at,
            )
            # Upsert steps
            for step in request.steps:
                await self._db.execute(
                    """INSERT INTO approval_steps
                       (request_id, approver_id, required, decided, decision, decided_at, comment)
                       VALUES ($1,$2,$3,$4,$5,$6,$7)
                       ON CONFLICT (request_id, approver_id) DO UPDATE SET
                         decided = EXCLUDED.decided,
                         decision = EXCLUDED.decision,
                         decided_at = EXCLUDED.decided_at,
                         comment = EXCLUDED.comment""",
                    request.id,
                    step.approver_id,
                    step.required,
                    step.decided,
                    step.decision.value,
                    step.decided_at,
                    step.comment,
                )
        except Exception:
            logger.warning("Failed to persist approval request %s", request.id, exc_info=True)

    async def _load_request(self, request_id: str) -> ApprovalRequest | None:
        row = await self._db.fetchrow("SELECT * FROM approval_requests WHERE id = $1", request_id)
        if not row:
            return None
        step_rows = await self._db.fetch(
            "SELECT * FROM approval_steps WHERE request_id = $1 ORDER BY id", request_id
        )
        steps = [
            ApprovalStep(
                approver_id=s["approver_id"],
                required=s["required"],
                decided=s["decided"],
                decision=ApprovalState(s["decision"]),
                decided_at=s["decided_at"],
                comment=s["comment"] or "",
            )
            for s in step_rows
        ]
        request = ApprovalRequest(
            id=row["id"],
            correlation_id=row["correlation_id"] or "",
            workflow_run_id=row["workflow_run_id"] or "",
            action_description=row["action_description"] or "",
            risk_level=RiskLevel(row["risk_level"]),
            state=ApprovalState(row["state"]),
            steps=steps,
            timeout_seconds=row["timeout_seconds"],
            escalation_target=row["escalation_target"],
            created_at=row["created_at"] or "",
            resolved_at=row["resolved_at"],
        )
        self._requests[request.id] = request
        return request
