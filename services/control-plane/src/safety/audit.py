"""Immutable audit trail — structured logging for all platform operations.

Persists events to Postgres when a database pool is provided. Falls back
to in-memory storage for local development and tests.

Event types:
- workflow_started, workflow_completed, workflow_failed
- model_call, tool_call
- connector_action
- approval_requested, approval_decided
- policy_evaluated, policy_violated
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


class AuditEventType(StrEnum):
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
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
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

    When a DatabasePool is attached via ``set_db()``, every event is
    INSERT-ed into the ``audit_events`` table (schema in migration 001).
    Without a pool the service keeps an in-memory list so the rest of
    the platform still works in local-dev mode.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._db: DatabasePool | None = None

    def set_db(self, db: DatabasePool) -> None:
        self._db = db

    async def log(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
        if self._db and self._db.connected:
            try:
                await self._db.execute(
                    """INSERT INTO audit_events
                       (id, timestamp, event_type, correlation_id, tenant_id,
                        actor, resource, action, details, model_input,
                        model_output, risk_level, outcome)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                    event.id,
                    event.timestamp,
                    event.event_type.value,
                    event.correlation_id,
                    event.tenant_id,
                    event.actor,
                    event.resource,
                    event.action,
                    json.dumps(event.details),
                    event.model_input,
                    event.model_output,
                    event.risk_level,
                    event.outcome,
                )
            except Exception:
                logger.warning("Failed to persist audit event %s", event.id, exc_info=True)
        return event

    async def log_workflow_started(self, correlation_id: str, workflow_name: str, tenant_id: str = "") -> AuditEvent:
        return await self.log(
            AuditEvent(
                event_type=AuditEventType.WORKFLOW_STARTED,
                correlation_id=correlation_id,
                tenant_id=tenant_id,
                action=workflow_name,
            )
        )

    async def log_workflow_completed(self, correlation_id: str, workflow_name: str, tenant_id: str = "") -> AuditEvent:
        return await self.log(
            AuditEvent(
                event_type=AuditEventType.WORKFLOW_COMPLETED,
                correlation_id=correlation_id,
                tenant_id=tenant_id,
                action=workflow_name,
            )
        )

    async def log_connector_action(
        self,
        correlation_id: str,
        connector: str,
        action: str,
        target: str,
        risk_level: str = "medium",
        outcome: str = "success",
    ) -> AuditEvent:
        return await self.log(
            AuditEvent(
                event_type=AuditEventType.CONNECTOR_ACTION,
                correlation_id=correlation_id,
                resource=connector,
                action=action,
                details={"target": target},
                risk_level=risk_level,
                outcome=outcome,
            )
        )

    async def log_model_call(
        self,
        correlation_id: str,
        model_name: str,
        input_text: str,
        output_text: str,
    ) -> AuditEvent:
        return await self.log(
            AuditEvent(
                event_type=AuditEventType.MODEL_CALL,
                correlation_id=correlation_id,
                resource=model_name,
                model_input=input_text,
                model_output=output_text,
            )
        )

    async def log_policy_violation(
        self,
        correlation_id: str,
        policy_name: str,
        violation: str,
    ) -> AuditEvent:
        return await self.log(
            AuditEvent(
                event_type=AuditEventType.POLICY_VIOLATED,
                correlation_id=correlation_id,
                action=policy_name,
                details={"violation": violation},
                outcome="blocked",
            )
        )

    async def query(
        self,
        event_type: AuditEventType | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        if self._db and self._db.connected:
            return await self._query_db(event_type, correlation_id, tenant_id, limit)
        return self._query_mem(event_type, correlation_id, tenant_id, limit)

    # -- private helpers -------------------------------------------------------

    def _query_mem(
        self,
        event_type: AuditEventType | None,
        correlation_id: str | None,
        tenant_id: str | None,
        limit: int,
    ) -> list[AuditEvent]:
        results = self._events
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if correlation_id:
            results = [e for e in results if e.correlation_id == correlation_id]
        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]
        return results[-limit:]

    async def _query_db(
        self,
        event_type: AuditEventType | None,
        correlation_id: str | None,
        tenant_id: str | None,
        limit: int,
    ) -> list[AuditEvent]:
        clauses: list[str] = []
        args: list[Any] = []
        idx = 1
        if event_type:
            clauses.append(f"event_type = ${idx}")
            args.append(event_type.value)
            idx += 1
        if correlation_id:
            clauses.append(f"correlation_id = ${idx}")
            args.append(correlation_id)
            idx += 1
        if tenant_id:
            clauses.append(f"tenant_id = ${idx}")
            args.append(tenant_id)
            idx += 1
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        args.append(limit)
        sql = f"SELECT * FROM audit_events{where} ORDER BY timestamp DESC LIMIT ${idx}"
        rows = await self._db.fetch(sql, *args)
        return [
            AuditEvent(
                id=r["id"],
                timestamp=r["timestamp"],
                event_type=AuditEventType(r["event_type"]),
                correlation_id=r["correlation_id"] or "",
                tenant_id=r["tenant_id"] or "",
                actor=r["actor"] or "",
                resource=r["resource"] or "",
                action=r["action"] or "",
                details=json.loads(r["details"]) if r["details"] else {},
                model_input=r["model_input"],
                model_output=r["model_output"],
                risk_level=r["risk_level"] or "low",
                outcome=r["outcome"] or "success",
            )
            for r in rows
        ]
