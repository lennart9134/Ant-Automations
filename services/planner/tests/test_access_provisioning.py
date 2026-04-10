"""Tests for the access provisioning workflow."""

from src.workflows.access_provisioning import (
    EventType,
    ExecutionMode,
    check_approvals,
    plan_actions,
)


def test_joiner_plan_creates_user_and_groups():
    state = {
        "event_type": EventType.JOINER.value,
        "execution_mode": ExecutionMode.SUPERVISED.value,
        "user_email": "alice@example.com",
        "department": "engineering",
    }
    result = plan_actions(state)
    action_types = [a["action_type"] for a in result["planned_actions"]]
    assert "create_user" in action_types
    assert "assign_group" in action_types
    assert "provision_app_access" in action_types


def test_leaver_plan_disables_and_revokes():
    state = {
        "event_type": EventType.LEAVER.value,
        "execution_mode": ExecutionMode.SUPERVISED.value,
        "user_email": "bob@example.com",
        "department": "finance",
    }
    result = plan_actions(state)
    action_types = [a["action_type"] for a in result["planned_actions"]]
    assert "disable_account" in action_types
    assert "revoke_all_sessions" in action_types
    assert "remove_group" in action_types


def test_autonomous_mode_approves_low_risk():
    state = {
        "event_type": EventType.JOINER.value,
        "execution_mode": ExecutionMode.AUTONOMOUS.value,
        "user_email": "carol@example.com",
        "department": "default",
        "planned_actions": [
            {"action_type": "assign_group", "risk_level": "low"},
        ],
    }
    result = check_approvals(state)
    assert result["status"] == "approved"
    assert result["pending_approvals"] == []


def test_observation_mode_requires_all_approvals():
    state = {
        "event_type": EventType.JOINER.value,
        "execution_mode": ExecutionMode.OBSERVATION.value,
        "user_email": "dan@example.com",
        "department": "default",
        "planned_actions": [
            {"action_type": "assign_group", "risk_level": "low"},
        ],
    }
    result = check_approvals(state)
    assert result["status"] == "awaiting_approval"
    assert len(result["pending_approvals"]) == 1
