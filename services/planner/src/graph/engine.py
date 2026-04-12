"""LangGraph workflow execution engine with shadow mode support.

Shadow mode (observation mode) logs every planned action and graph
transition without executing connector calls. This enables safe pilot
onboarding: customers see what the system *would* do before granting it
autonomous permissions.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)

# Shadow mode can be enabled globally via env var or per-request via payload
SHADOW_MODE = os.getenv("SHADOW_MODE", "false").lower() == "true"


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"
    SHADOW = "shadow"


@dataclass
class WorkflowState:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    run_id: str
    status: str
    results: list[dict[str, Any]]
    shadow: bool = False


class WorkflowEngine:
    """Manages LangGraph workflow registration and execution.

    Graphs are compiled once at registration time and reused for every
    execution, avoiding the overhead of recompilation on each request.

    Shadow mode:
    - Enabled globally via SHADOW_MODE=true or per-request via execution_mode=observation
    - Runs the full planning and verification pipeline
    - Logs all planned actions in detail
    - Does NOT dispatch to connectors or NATS
    - Returns results tagged with shadow=True
    """

    def __init__(self) -> None:
        self._graphs: dict[str, StateGraph] = {}
        self._compiled: dict[str, Any] = {}
        self._shadow_log: list[dict[str, Any]] = []
        self.event_bus = None

    async def start(self) -> None:
        from ..workflows.access_provisioning import register_access_provisioning
        from ..workflows.ticket_triage import register_ticket_triage

        register_access_provisioning(self)
        register_ticket_triage(self)

    async def stop(self) -> None:
        pass

    def register(self, name: str, graph: StateGraph) -> None:
        self._graphs[name] = graph
        self._compiled[name] = graph.compile()

    def _is_shadow(self, payload: dict[str, Any]) -> bool:
        """Check if this execution should run in shadow mode."""
        if SHADOW_MODE:
            return True
        return payload.get("execution_mode") == "observation"

    async def execute(self, workflow_name: str, payload: dict[str, Any]) -> WorkflowResult:
        if workflow_name not in self._compiled:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        compiled = self._compiled[workflow_name]
        shadow = self._is_shadow(payload)

        state = WorkflowState(
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            context=payload,
        )

        if shadow:
            # Force observation mode in the payload so check_approvals marks all as needing approval
            payload = {**payload, "execution_mode": "observation"}

        result_state = await compiled.ainvoke(
            {"state": state, **payload},
        )

        status = result_state.get("status", WorkflowStatus.COMPLETED.value)
        results = result_state.get("results", [])

        if shadow:
            status = WorkflowStatus.SHADOW.value
            self._log_shadow_run(state.run_id, workflow_name, payload, results)

        return WorkflowResult(
            run_id=state.run_id,
            status=status,
            results=results,
            shadow=shadow,
        )

    def _log_shadow_run(
        self,
        run_id: str,
        workflow_name: str,
        payload: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        entry = {
            "run_id": run_id,
            "workflow": workflow_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "planned_actions": results,
            "payload_keys": list(payload.keys()),
            "mode": "shadow",
        }
        self._shadow_log.append(entry)
        logger.info(
            "SHADOW RUN [%s] workflow=%s actions=%d",
            run_id,
            workflow_name,
            len(results),
        )
        for action in results:
            if isinstance(action, dict):
                logger.info(
                    "  SHADOW ACTION: %s → %s (risk=%s)",
                    action.get("action_type", "unknown"),
                    action.get("target", "?"),
                    action.get("risk_level", "?"),
                )

    def get_shadow_log(self) -> list[dict[str, Any]]:
        """Return the shadow mode execution log for review."""
        return list(self._shadow_log)
