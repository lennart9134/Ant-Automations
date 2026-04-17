"""Tests for the min-employee aggregation gate.

These tests pin the compliance promise made in Business Plan v4.5 §11A.5 and
docs/adr/008-hdbscan-pattern-classifier.md. If one of them fails, *do not* relax the
assertion — fix the pipeline. The test failure means the classifier is about to emit a
candidate that would expose individual-employee behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.classifier import WorkflowCandidate, enforce_aggregation_gate
from src.constraints import MIN_EMPLOYEE_AGGREGATION, AggregationGateViolation


def _make_candidate(employee_count: int) -> WorkflowCandidate:
    now = datetime.now(UTC)
    return WorkflowCandidate(
        tenant_id="test-tenant",
        cluster_label=1,
        sample_sequence=("servicenow.incident.create", "entra_id.user.lookup"),
        occurrences_per_week=10.0,
        avg_duration_ms=90_000,
        estimated_fte_hours_per_week=5.0,
        estimated_annual_cost_eur=12_000.0,
        feasibility_score=0.9,
        confidence_score=0.8,
        employee_count=employee_count,
        first_observed=now,
        last_observed=now,
    )


def test_gate_is_exactly_three() -> None:
    """The gate value is not a tuning parameter. If this test fails, someone lowered the gate."""
    assert MIN_EMPLOYEE_AGGREGATION == 3


@pytest.mark.parametrize("count", [0, 1, 2])
def test_gate_rejects_below_threshold(count: int) -> None:
    candidate = _make_candidate(employee_count=count)
    with pytest.raises(AggregationGateViolation):
        enforce_aggregation_gate(candidate)


@pytest.mark.parametrize("count", [3, 4, 10, 100])
def test_gate_accepts_at_or_above_threshold(count: int) -> None:
    candidate = _make_candidate(employee_count=count)
    # Must not raise.
    enforce_aggregation_gate(candidate)


def test_violation_message_points_to_compliance_docs() -> None:
    """The exception must carry the breadcrumb so an on-call engineer hits the ADR fast."""
    candidate = _make_candidate(employee_count=1)
    with pytest.raises(AggregationGateViolation) as info:
        enforce_aggregation_gate(candidate)
    msg = str(info.value)
    assert "§11A.5" in msg
    assert "ADR 008" in msg
