"""Tests for the safety layer."""

from src.safety.approvals import ApprovalChainService, ApprovalState, RiskLevel
from src.safety.policy import PolicyDecision, create_default_policies


def test_low_risk_auto_approved():
    svc = ApprovalChainService()
    req = svc.create_request(
        workflow_run_id="run-1",
        action_description="Assign user to group",
        risk_level=RiskLevel.LOW,
        approvers=["approver-1"],
    )
    assert req.state == ApprovalState.APPROVED


def test_medium_risk_requires_approval():
    svc = ApprovalChainService()
    req = svc.create_request(
        workflow_run_id="run-2",
        action_description="Create user account",
        risk_level=RiskLevel.MEDIUM,
        approvers=["approver-1"],
    )
    assert req.state == ApprovalState.PENDING


def test_high_risk_multi_approver():
    svc = ApprovalChainService()
    req = svc.create_request(
        workflow_run_id="run-3",
        action_description="Delete user account",
        risk_level=RiskLevel.HIGH,
        approvers=["approver-1", "approver-2"],
    )
    assert req.state == ApprovalState.PENDING

    svc.decide(req.id, "approver-1", approved=True)
    assert req.state == ApprovalState.PENDING  # still waiting for second approver

    svc.decide(req.id, "approver-2", approved=True)
    assert req.state == ApprovalState.APPROVED


def test_unknown_approver_raises():
    """Deciding with an approver_id not in the chain must raise ValueError."""
    svc = ApprovalChainService()
    req = svc.create_request(
        workflow_run_id="run-4",
        action_description="Test unknown approver",
        risk_level=RiskLevel.MEDIUM,
        approvers=["approver-1"],
    )

    try:
        svc.decide(req.id, "unknown-approver", approved=True)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_policy_blocks_admin_deletion():
    engine = create_default_policies()
    result = engine.evaluate({"action": "delete_user", "target_role": "admin", "risk_level": "high"})
    assert result.decision == PolicyDecision.BLOCK


def test_policy_allows_low_risk():
    engine = create_default_policies()
    result = engine.evaluate({"action": "assign_group", "risk_level": "low"})
    assert result.decision == PolicyDecision.ALLOW
