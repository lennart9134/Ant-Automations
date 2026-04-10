"""Policy engine — declarative rules for action governance.

Policies evaluate connector actions and workflow steps against configurable
rules to determine whether they should proceed, require approval, or be blocked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class PolicyConditionOp(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    MATCHES = "matches"


@dataclass
class PolicyCondition:
    field: str
    op: PolicyConditionOp
    value: Any


@dataclass
class PolicyRule:
    """A single policy rule with conditions and a decision."""

    id: str
    name: str
    description: str = ""
    conditions: list[PolicyCondition] = field(default_factory=list)
    decision: PolicyDecision = PolicyDecision.REQUIRE_APPROVAL
    priority: int = 0  # higher = evaluated first


@dataclass
class PolicyEvaluation:
    rule_id: str
    rule_name: str
    decision: PolicyDecision
    matched_conditions: list[str]


class PolicyEngine:
    """Evaluates actions against configured policy rules.

    Rules are evaluated in priority order. First matching rule wins.
    If no rule matches, the default decision applies.
    """

    def __init__(self, default_decision: PolicyDecision = PolicyDecision.REQUIRE_APPROVAL) -> None:
        self._rules: list[PolicyRule] = []
        self._default_decision = default_decision

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, context: dict[str, Any]) -> PolicyEvaluation:
        for rule in self._rules:
            matched = []
            all_match = True
            for condition in rule.conditions:
                value = context.get(condition.field)
                if self._check_condition(condition, value):
                    matched.append(condition.field)
                else:
                    all_match = False
                    break

            if all_match:
                return PolicyEvaluation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    decision=rule.decision,
                    matched_conditions=matched,
                )

        return PolicyEvaluation(
            rule_id="default",
            rule_name="default_policy",
            decision=self._default_decision,
            matched_conditions=[],
        )

    @staticmethod
    def _check_condition(condition: PolicyCondition, value: Any) -> bool:
        if condition.op == PolicyConditionOp.EQUALS:
            return value == condition.value
        elif condition.op == PolicyConditionOp.NOT_EQUALS:
            return value != condition.value
        elif condition.op == PolicyConditionOp.IN:
            return value in condition.value
        elif condition.op == PolicyConditionOp.NOT_IN:
            return value not in condition.value
        elif condition.op == PolicyConditionOp.CONTAINS:
            return condition.value in str(value)
        elif condition.op == PolicyConditionOp.MATCHES:
            return bool(re.search(condition.value, str(value)))
        return False


def create_default_policies() -> PolicyEngine:
    """Create the standard policy set for enterprise deployments."""
    engine = PolicyEngine()

    engine.add_rule(PolicyRule(
        id="block-admin-delete",
        name="Block admin account deletion",
        description="Never allow deletion of admin accounts without explicit override",
        conditions=[
            PolicyCondition(field="action", op=PolicyConditionOp.EQUALS, value="delete_user"),
            PolicyCondition(field="target_role", op=PolicyConditionOp.EQUALS, value="admin"),
        ],
        decision=PolicyDecision.BLOCK,
        priority=100,
    ))

    engine.add_rule(PolicyRule(
        id="auto-approve-low-risk",
        name="Auto-approve low-risk actions",
        conditions=[
            PolicyCondition(field="risk_level", op=PolicyConditionOp.EQUALS, value="low"),
        ],
        decision=PolicyDecision.ALLOW,
        priority=10,
    ))

    engine.add_rule(PolicyRule(
        id="require-approval-high-risk",
        name="Require multi-approval for high-risk actions",
        conditions=[
            PolicyCondition(field="risk_level", op=PolicyConditionOp.EQUALS, value="high"),
        ],
        decision=PolicyDecision.REQUIRE_APPROVAL,
        priority=50,
    ))

    return engine
