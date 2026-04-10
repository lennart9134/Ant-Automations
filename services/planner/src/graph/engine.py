"""LangGraph workflow execution engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langgraph.graph import StateGraph, END


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


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


class WorkflowEngine:
    """Manages LangGraph workflow registration and execution.

    Graphs are compiled once at registration time and reused for every
    execution, avoiding the overhead of recompilation on each request.
    """

    def __init__(self) -> None:
        self._graphs: dict[str, StateGraph] = {}
        self._compiled: dict[str, Any] = {}

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

    async def execute(self, workflow_name: str, payload: dict[str, Any]) -> WorkflowResult:
        if workflow_name not in self._compiled:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        compiled = self._compiled[workflow_name]

        state = WorkflowState(
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            context=payload,
        )

        result_state = await compiled.ainvoke(
            {"state": state, **payload},
        )

        return WorkflowResult(
            run_id=state.run_id,
            status=result_state.get("status", WorkflowStatus.COMPLETED.value),
            results=result_state.get("results", []),
        )
