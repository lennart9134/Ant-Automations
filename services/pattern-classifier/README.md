# pattern-classifier

**Layer:** Learn (step 3–4 of the 9-step platform loop).
**Port:** 8007.
**Role:** Consume normalised observation events, extract recurring sequences, cluster into
workflow candidates with HDBSCAN, score feasibility and savings, and emit candidates for the
Propose layer.

## Scope (v4.5 §4.1.2, §5.2 step 3–4)

- Subscribe to `observation.events.>` on NATS JetStream.
- Extract sliding-window sequences (default window 20, min recurrence 5, configurable).
- Embed sequences using the Qwen3-30B-A3B planner (shared with `services/planner`).
- Cluster embeddings with HDBSCAN — density-based, handles variable-length sequences and noise.
- Compute occurrences/week, avg duration, FTE hours/week, and annual cost.
- Score feasibility against the connector registry (`services/connectors`).
- Emit candidates to `observation.workflow_candidates.{tenant_id}` (consumed by Propose).
- Enforce the **min-3-employee aggregation gate** (see §11A.5, ADR 008).

## The min-3-employee aggregation gate

Any pattern that is observed in fewer than **three** distinct employees is discarded
before it can become a workflow candidate. This is a hard architectural constraint, not a
configurable setting — see [ADR 008](../../docs/adr/008-hdbscan-pattern-classifier.md) and
business-plan §11A.5 product response #2.

The single source of truth for the threshold is
[`src/constraints.py`](src/constraints.py). The Propose-layer schema has a belt-and-braces
`CHECK (employee_count >= 3)` on `observation.proposals`.

## What is NOT in this service

- No storage of raw events — that lives in `observation.observation_events` and is read-only here.
- No proposal review UI — that is the control plane.
- No per-employee reporting. The classifier only ever emits aggregate candidates.

## Current state

Scaffold. `src/main.py` exposes the API shape. `src/constraints.py` holds the gate threshold.
`src/classifier.py` has the pipeline skeleton with type-complete function signatures. The real
sequence mining and HDBSCAN wiring is the next pull request.

### Next-step TODOs

- [ ] Wire Qwen3 embeddings via SGLang (`services/vision` or dedicated planner serving).
- [ ] Implement sliding-window extraction from `observation.observed_sequences`.
- [ ] Implement HDBSCAN clustering with tenant-scoped batch jobs.
- [ ] Emit candidates to Propose via NATS + Postgres insert to `observation.workflow_candidates`.
- [ ] Back-test against labelled internal observation data before first customer deployment.
- [ ] Add observation-coverage and pattern-discovery-rate metrics to `libs/observability`.

## Related business-plan sections

- §4.1.2 — Pattern Classifier (Learn)
- §9 — Software Stack (Qwen3 + HDBSCAN)
- §11A.5 — Employee Monitoring Law, product response #2 (aggregation threshold)
- §14 — Risks (pattern classifier false positives → confidence scores, observation window)
- §15.1 — Pattern discovery rate, proposal acceptance rate
