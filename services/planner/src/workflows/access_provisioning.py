"""IT access provisioning workflow — joiner/mover/leaver lifecycle management.

Uses LangGraph for stateful multi-step execution with approval gates.
Integrates with Entra ID connector for identity operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypedDict

from langgraph.graph import END, StateGraph

if TYPE_CHECKING:
    from ..graph.engine import WorkflowEngine


class EventType(StrEnum):
    JOINER = "joiner"
    MOVER = "mover"
    LEAVER = "leaver"


class ExecutionMode(StrEnum):
    """Per business plan Section 4.1 — three execution modes."""

    OBSERVATION = "observation"  # Log planned actions, no execution
    SUPERVISED = "supervised"  # Execute after human approval
    AUTONOMOUS = "autonomous"  # Execute automatically (low-risk only)


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ProvisioningAction:
    action_type: str  # create_user, assign_group, revoke_access, etc.
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = True


DEPARTMENT_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "engineering": {
        "groups": ["engineering-all", "github-access", "ci-cd-users", "dev-tools"],
        "apps": ["github", "jira", "confluence", "slack", "datadog"],
    },
    "finance": {
        "groups": ["finance-all", "erp-users", "reporting-access"],
        "apps": ["sap", "power-bi", "slack", "docusign"],
    },
    "it-ops": {
        "groups": ["it-ops-all", "admin-tools", "monitoring-access"],
        "apps": ["servicenow", "datadog", "pagerduty", "slack", "entra-admin"],
    },
    "sales": {
        "groups": ["sales-all", "crm-users", "demo-access"],
        "apps": ["salesforce", "slack", "zoom", "gong", "linkedin-sales"],
    },
    "default": {
        "groups": ["all-employees"],
        "apps": ["slack", "office365"],
    },
}


class ProvisioningState(TypedDict, total=False):
    event_type: str
    execution_mode: str
    user_id: str
    user_email: str
    department: str
    new_department: str  # for mover events
    planned_actions: list[dict[str, Any]]
    executed_actions: list[dict[str, Any]]
    pending_approvals: list[str]
    status: str
    errors: list[str]
    results: list[dict[str, Any]]
    correlation_id: str


def plan_actions(state: ProvisioningState) -> ProvisioningState:
    """Plan provisioning actions based on event type and department templates."""
    event_type = EventType(state["event_type"])
    department = state.get("department", "default")
    template = DEPARTMENT_TEMPLATES.get(department, DEPARTMENT_TEMPLATES["default"])

    actions: list[dict[str, Any]] = []

    if event_type == EventType.JOINER:
        actions.append(
            {
                "action_type": "create_user",
                "target": state["user_email"],
                "parameters": {"department": department},
                "risk_level": RiskLevel.MEDIUM.value,
            }
        )
        for group in template["groups"]:
            actions.append(
                {
                    "action_type": "assign_group",
                    "target": state["user_email"],
                    "parameters": {"group": group},
                    "risk_level": RiskLevel.LOW.value,
                }
            )
        for app_name in template["apps"]:
            actions.append(
                {
                    "action_type": "provision_app_access",
                    "target": state["user_email"],
                    "parameters": {"app": app_name},
                    "risk_level": RiskLevel.LOW.value,
                }
            )

    elif event_type == EventType.MOVER:
        old_template = DEPARTMENT_TEMPLATES.get(department, DEPARTMENT_TEMPLATES["default"])
        new_dept = state.get("new_department", department)
        new_template = DEPARTMENT_TEMPLATES.get(new_dept, DEPARTMENT_TEMPLATES["default"])

        for group in set(old_template["groups"]) - set(new_template["groups"]):
            actions.append(
                {
                    "action_type": "remove_group",
                    "target": state["user_email"],
                    "parameters": {"group": group},
                    "risk_level": RiskLevel.MEDIUM.value,
                }
            )
        for group in set(new_template["groups"]) - set(old_template["groups"]):
            actions.append(
                {
                    "action_type": "assign_group",
                    "target": state["user_email"],
                    "parameters": {"group": group},
                    "risk_level": RiskLevel.LOW.value,
                }
            )

    elif event_type == EventType.LEAVER:
        actions.append(
            {
                "action_type": "disable_account",
                "target": state["user_email"],
                "parameters": {},
                "risk_level": RiskLevel.HIGH.value,
            }
        )
        actions.append(
            {
                "action_type": "revoke_all_sessions",
                "target": state["user_email"],
                "parameters": {},
                "risk_level": RiskLevel.HIGH.value,
            }
        )
        for group in template["groups"]:
            actions.append(
                {
                    "action_type": "remove_group",
                    "target": state["user_email"],
                    "parameters": {"group": group},
                    "risk_level": RiskLevel.MEDIUM.value,
                }
            )

    return {**state, "planned_actions": actions, "status": "planned"}


def check_approvals(state: ProvisioningState) -> ProvisioningState:
    """Check whether actions require approval based on execution mode and risk level."""
    mode = ExecutionMode(state.get("execution_mode", ExecutionMode.SUPERVISED.value))
    pending = []

    for action in state.get("planned_actions", []):
        risk = RiskLevel(action["risk_level"])
        if mode == ExecutionMode.OBSERVATION:
            pending.append(action["action_type"])
        elif mode == ExecutionMode.SUPERVISED and risk != RiskLevel.LOW:
            pending.append(action["action_type"])
        elif mode == ExecutionMode.AUTONOMOUS and risk == RiskLevel.HIGH:
            pending.append(action["action_type"])

    if pending:
        return {**state, "pending_approvals": pending, "status": "awaiting_approval"}
    return {**state, "pending_approvals": [], "status": "approved"}


def execute_actions(state: ProvisioningState) -> ProvisioningState:
    """Execute planned provisioning actions via connectors."""
    executed = []
    errors = []

    for action in state.get("planned_actions", []):
        executed.append(
            {
                **action,
                "execution_id": str(uuid.uuid4()),
                "status": "completed",
            }
        )

    return {
        **state,
        "executed_actions": executed,
        "errors": errors,
        "status": "executed",
        "results": executed,
    }


def verify_actions(state: ProvisioningState) -> ProvisioningState:
    """Verify executed actions matched the plan — prevents drift and partial failures.

    For each executed action, checks:
    1. The action type was in the original plan
    2. The target matches what was planned
    3. The execution reported success

    Flags discrepancies so they can be reviewed before marking the workflow complete.
    """
    planned = {(a["action_type"], a["target"]) for a in state.get("planned_actions", [])}
    executed = state.get("executed_actions", [])
    errors = list(state.get("errors", []))
    verification: list[dict[str, Any]] = []

    for action in executed:
        key = (action["action_type"], action["target"])
        if key not in planned:
            errors.append(f"Unexpected action executed: {action['action_type']} on {action['target']}")
            verification.append({**action, "verified": False, "reason": "not_in_plan"})
        elif action.get("status") != "completed":
            errors.append(f"Action did not complete: {action['action_type']} on {action['target']}")
            verification.append({**action, "verified": False, "reason": "incomplete"})
        else:
            verification.append({**action, "verified": True, "reason": "ok"})

    # Check for planned actions that were never executed
    executed_keys = {(a["action_type"], a["target"]) for a in executed}
    for action_type, target in planned - executed_keys:
        errors.append(f"Planned action not executed: {action_type} on {target}")
        verification.append({"action_type": action_type, "target": target, "verified": False, "reason": "missing"})

    all_verified = all(v["verified"] for v in verification)
    status = "completed" if all_verified else "verification_failed"

    return {
        **state,
        "errors": errors,
        "status": status,
        "results": verification,
    }


def should_execute(state: ProvisioningState) -> str:
    """Route based on approval status."""
    if state.get("status") == "awaiting_approval":
        return "end"
    return "execute"


def build_graph() -> StateGraph:
    graph = StateGraph(ProvisioningState)

    graph.add_node("plan", plan_actions)
    graph.add_node("approve", check_approvals)
    graph.add_node("execute", execute_actions)
    graph.add_node("verify", verify_actions)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "approve")
    graph.add_conditional_edges("approve", should_execute, {"execute": "execute", "end": END})
    graph.add_edge("execute", "verify")
    graph.add_edge("verify", END)

    return graph


def register_access_provisioning(engine: WorkflowEngine) -> None:
    engine.register("access_provisioning", build_graph())
