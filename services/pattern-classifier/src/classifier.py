"""Pattern classifier pipeline — sequence extraction, embedding, clustering, scoring.

This is the scaffold. The function signatures and the aggregation gate are production-shaped;
the bodies of the embedding and clustering steps are stubs until Qwen3 serving is wired up.

Pipeline (v4.5 §4.1.2):
    normalised events → sliding-window sequences → embeddings → HDBSCAN → candidates → filter
                                                                                        ↑
                                                           MIN_EMPLOYEE_AGGREGATION gate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .constraints import (
    MIN_EMPLOYEE_AGGREGATION,
    MIN_OBSERVATION_WINDOW_DAYS,
    MIN_PATTERN_RECURRENCE,
    AggregationGateViolation,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NormalisedEvent:
    tenant_id: str
    actor_id: str
    timestamp: datetime
    action_type: str
    source_application: str
    target_application: str
    duration_ms: int


@dataclass
class ObservedSequence:
    tenant_id: str
    actor_id: str
    action_sequence: tuple[str, ...]
    occurrences: int
    total_duration_ms: int
    first_seen: datetime
    last_seen: datetime


@dataclass
class WorkflowCandidate:
    tenant_id: str
    cluster_label: int
    sample_sequence: tuple[str, ...]
    occurrences_per_week: float
    avg_duration_ms: int
    estimated_fte_hours_per_week: float
    estimated_annual_cost_eur: float
    feasibility_score: float
    confidence_score: float
    employee_count: int
    first_observed: datetime
    last_observed: datetime
    actor_id_hashes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stages. Kept as free functions so they can be unit-tested in isolation.
# ---------------------------------------------------------------------------
def extract_sequences(
    events: Iterable[NormalisedEvent],
    *,
    window: int = 20,
    min_recurrence: int = MIN_PATTERN_RECURRENCE,
) -> list[ObservedSequence]:
    """Sliding-window sequence mining over a stream of normalised events.

    TODO(v4.5-learn): implement. Scaffold below just returns an empty list so downstream
    type-checking passes. The real implementation reads from observation.observation_events.
    """
    logger.debug(
        "extract_sequences called (window=%d, min_recurrence=%d) — stub",
        window,
        min_recurrence,
    )
    return []


def embed_sequences(sequences: list[ObservedSequence]) -> list[list[float]]:
    """Produce action-sequence embeddings via Qwen3-30B-A3B.

    TODO(v4.5-learn): call SGLang serving for Qwen3 embeddings. Returning a fixed-dim zero vector
    keeps the pipeline type-correct in the meantime.
    """
    return [[0.0] * 16 for _ in sequences]


def cluster_embeddings(
    embeddings: list[list[float]],
    *,
    min_cluster_size: int = MIN_EMPLOYEE_AGGREGATION,
) -> list[int]:
    """HDBSCAN clustering on embeddings. Returns a cluster label per input embedding.

    NOTE: `min_cluster_size` defaults to MIN_EMPLOYEE_AGGREGATION so that HDBSCAN cannot form a
    cluster that is too small to pass the aggregation gate downstream. The gate itself is still
    enforced explicitly in `enforce_aggregation_gate` — defence in depth.

    TODO(v4.5-learn): wire real HDBSCAN. Scaffold returns -1 (noise) for every input.
    """
    return [-1] * len(embeddings)


def enforce_aggregation_gate(candidate: WorkflowCandidate) -> WorkflowCandidate:
    """Raise if a candidate violates the min-employee aggregation gate.

    This is the primary enforcement point. The Postgres CHECK constraint on
    observation.proposals is belt-and-braces — but the classifier must never construct a
    candidate that would hit that CHECK. That would indicate a pipeline bug.
    """
    if candidate.employee_count < MIN_EMPLOYEE_AGGREGATION:
        raise AggregationGateViolation(
            f"candidate for cluster={candidate.cluster_label} "
            f"has employee_count={candidate.employee_count} "
            f"< MIN_EMPLOYEE_AGGREGATION={MIN_EMPLOYEE_AGGREGATION}. "
            "This candidate must not be surfaced. See §11A.5 and ADR 008."
        )
    return candidate


def score_feasibility(candidate: WorkflowCandidate, connector_registry: set[str]) -> float:
    """Fraction of steps in the candidate sequence that can be API-automated.

    TODO(v4.5-learn): real implementation consults connector capabilities. Stub scores by simple
    string matching against the registry.
    """
    if not candidate.sample_sequence:
        return 0.0
    hits = sum(1 for step in candidate.sample_sequence if step.split(".")[0] in connector_registry)
    return hits / len(candidate.sample_sequence)
