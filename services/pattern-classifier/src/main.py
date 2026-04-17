"""Learn-layer service — pattern classifier.

Exposes the classifier API and (when the batch job is implemented) runs the mining pipeline
against normalised observation events.

Business-plan references:
    §4.1.2 — Pattern Classifier
    §5.2   — 9-step platform loop, steps 3–4
    §11A.5 — Employee monitoring law, product response #2 (aggregation threshold)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .constraints import (
    MIN_EMPLOYEE_AGGREGATION,
    MIN_OBSERVATION_WINDOW_DAYS,
    MIN_PATTERN_RECURRENCE,
    AggregationGateViolation,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "pattern-classifier starting (MIN_EMPLOYEE_AGGREGATION=%d)",
        MIN_EMPLOYEE_AGGREGATION,
    )
    yield


app = FastAPI(
    title="Ant Automations — Pattern Classifier",
    version="0.1.0",
    description=(
        "Learn-layer service. Mines recurring sequences from normalised observation events, "
        "clusters them with HDBSCAN, scores feasibility, and emits candidates to the Propose "
        f"layer. Enforces a min-{MIN_EMPLOYEE_AGGREGATION}-employee aggregation gate."
    ),
    lifespan=lifespan,
)


@app.get("/healthz")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "pattern-classifier",
        "gate": {
            "min_employee_aggregation": MIN_EMPLOYEE_AGGREGATION,
            "min_observation_window_days": MIN_OBSERVATION_WINDOW_DAYS,
            "min_pattern_recurrence": MIN_PATTERN_RECURRENCE,
        },
    }


@app.get("/api/v1/constraints")
async def constraints() -> dict:
    """Expose the hard architectural constraints so operators / auditors can verify them.

    Anyone reviewing a pilot deployment can curl this endpoint and see the constraint values
    that are actually compiled into the running service. If the values differ from the ADR or
    the works-council template, *that is a compliance incident.*
    """
    return {
        "min_employee_aggregation": MIN_EMPLOYEE_AGGREGATION,
        "min_observation_window_days": MIN_OBSERVATION_WINDOW_DAYS,
        "min_pattern_recurrence": MIN_PATTERN_RECURRENCE,
        "rationale": (
            "These constants are fixed by the v4.5 architecture and the works-council "
            "Betriebsvereinbarung. They are not configurable at runtime. See "
            "docs/adr/008-hdbscan-pattern-classifier.md and Business Plan v4.5 §11A.5."
        ),
    }


@app.post("/api/v1/classifier/run")
async def run_classifier(tenant_id: str) -> dict:
    """Trigger a classifier batch run for one tenant.

    TODO(v4.5-learn): wire the real pipeline. Scaffold returns a no-op response so the
    control plane can already integrate against the endpoint shape.
    """
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")
    try:
        return {
            "tenant_id": tenant_id,
            "status": "stub",
            "candidates_emitted": 0,
            "notes": (
                "Scaffold — real classifier pipeline pending. "
                f"Gate: employee_count >= {MIN_EMPLOYEE_AGGREGATION}."
            ),
        }
    except AggregationGateViolation as exc:
        # Surfaced here for symmetry; the gate also raises inside classifier.enforce_aggregation_gate.
        raise HTTPException(status_code=409, detail=str(exc))
