# observation-ingest

**Layer:** Watch (step 1–2 of the 9-step platform loop).
**Port:** 8006.
**Role:** Accept events from the desktop agent and browser extension, validate them against the
privacy-by-design event schema, normalise them into the unified action schema, publish them to
NATS JetStream, and expose employee-facing status endpoints.

## Scope (v4.5 §4.1.1, §5.2 step 1–2)

- Ingest `POST /api/v1/events/batch` from `clients/desktop-agent` and `clients/browser-extension`.
- Validate — reject any payload field that looks like content (keystroke buffers, clipboard text,
  form values, image bytes, URLs with query-string secrets). This is the **privacy hard-stop**.
- Normalise to the canonical schema:
  `{timestamp, tenant_id, actor_id, action_type, source_application, target_application,
    duration_ms, metadata, capture_channel}`.
- Publish each normalised event to `observation.events.{tenant_id}.{capture_channel}` on NATS
  JetStream (dedicated stream `OBSERVATION`, separate retention from application streams).
- Serve `GET /api/v1/observation/status/{actor_id}` for the employee transparency dashboard.

## What is NOT in this service

- No storage of observation events — the ingest path is stateless; persistence is downstream.
- No pattern mining — that is `services/pattern-classifier`.
- No per-employee reporting ever — see `docs/adr/008-hdbscan-pattern-classifier.md`.

## Current state

This service is a **scaffold**. `src/main.py` exposes `/healthz`, the event-batch endpoint, and
the employee-status endpoint. The privacy-validator has the content-field denylist wired in and
unit-tested. Integration with the desktop agent and browser extension is next.

### Next-step TODOs

- [ ] Wire real JetStream publishing (currently logs events in stub mode when NATS unavailable).
- [ ] Add OTel spans around the ingest path.
- [ ] Add per-tenant observation-scope enforcement (minimal vs application vs action).
- [ ] Persist a compact "last-event" cache in Redis for the employee transparency dashboard.
- [ ] Add rate limiting per agent (defence against misbehaving endpoints).
- [ ] Run privacy fuzz tests against the denylist before first pilot.

## Related business-plan sections

- §4.1.1 — Observation Layer / Watch
- §9 — Software Stack (NATS JetStream)
- §11A.5 — Employee Monitoring Law (product response #3 "configurable observation scope")
- §14 — Risks ("observation data breach" → isolated partition, shortest feasible retention)
