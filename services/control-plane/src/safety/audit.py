"""Immutable audit trail — structured logging for all platform operations.

Event types:
- workflow_started, workflow_completed, workflow_failed
- model_call, tool_call
- connector_action
- approval_requested, approval_decided
- policy_evaluated, policy_violated
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditEventType(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    CONNECTOR_ACTION = "connector_action"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_VIOLATED = "policy_violated"


@dataclass
class AuditEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: AuditEventType = AuditEventType.WORKFLOW_STARTED
    correlation_id: str = ""
    tenant_id: str = ""
    actor: str = ""
    resource: str = ""
    action: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    model_input: str | None = None
    model_output: str | None = None
    risk_level: str = "low"
    outcome: str = "success"


class AuditTrailService:
    """Append-only audit trail with structured event logging.

    In production, events are persisted to Postgres with SIEM export
    via OpenTelemetry log exporter.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def log(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
        return event

    def log_workflow_started(self, correlation_id: str, workflow_name: str, tenant_id: str = "") -> AuditEvent:
        return self.log(AuditEvent(
            event_type=AuditEventType.WORKFLOW_STARTED,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            action=workflow_name,
        ))

    def log_workflow_completed(self, correlation_id: str, workflow_name: str, tenant_id: str = "") -> AuditEvent:
        return self.log(AuditEvent(
            event_type=AuditEventType.WORKFLOW_COMPLETED,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            action=workflow_name,
        ))

    def log_connector_action(
        self,
        correlation_id: str,
        connector: str,
        action: str,
        target: str,
        risk_level: str = "medium",
        outcome: str = "success",
    ) -> AuditEvent:
        return self.log(AuditEvent(
            event_type=AuditEventType.CONNECTOR_ACTION,
            correlation_id=correlation_id,
            resource=connector,
            action=action,
            details={"target": target},
            risk_level=risk_level,
            outcome=outcome,
        ))

    def log_model_call(
        self,
        correlation_id: str,
        model_name: str,
        input_text: str,
        output_text: str,
    ) -> AuditEvent:
        return self.log(AuditEvent(
            event_type=AuditEventType.MODEL_CALL,
            correlation_id=correlation_id,
            resource=model_name,
            model_input=input_text,
            model_output=output_text,
        ))

    def log_policy_violation(
        self,
        correlation_id: str,
        policy_name: str,
        violation: str,
    ) -> AuditEvent:
        return self.log(AuditEvent(
            event_type=AuditEventType.POLICY_VIOLATED,
            correlation_id=correlation_id,
            action=policy_name,
            details={"violation": violation},
            outcome="blocked",
        ))

    def query(
        self,
        event_type: AuditEventType | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        results = self._events
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if correlation_id:
            results = [e for e in results if e.correlation_id == correlation_id]
        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]
        return results[-limit:]
