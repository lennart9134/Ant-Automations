# ADR 009: Split retention and schema isolation for observation data

## Status
Accepted

## Context
Before v4.5 the platform had a single `tenants.retention_days` column
covering execution audit logs. The v4.5 Watch layer introduces two
materially different data categories:

- **Raw observation events** — per-employee per-action records. Very
  high volume; short useful life; high privacy sensitivity.
- **Aggregated patterns** — workflow candidates and proposal decisions
  derived from raw events, only after passing the k≥3 aggregation gate.
  Moderate volume; long useful life (the Govern layer references them for
  months); much lower privacy sensitivity.

Treating both under a single retention knob would either:

- Force aggregated patterns to be deleted too early (breaking the
  Propose / Govern loop), or
- Keep raw events too long (bloating storage and expanding breach blast
  radius far beyond what the Betriebsvereinbarung template §6 and
  employee-privacy-notice §5 commit to).

A second concern: the execution services (planner, connectors,
control-plane, workers, vision) have broad database credentials because
they write audit logs. Storing raw observation data in the same schema
means a misconfigured query in any of those services could accidentally
read employee observation records.

## Decision
Two changes:

1. **Split retention columns on `tenants`:**
   - `audit_retention_days` (existing; was `retention_days`, renamed)
   - `observation_retention_raw_days` — default **90**
   - `observation_retention_aggregated_days` — default **365**
   - `observation_scope` — enum `{minimal, standard}`, default `minimal`

   Migration: `services/control-plane/migrations/versions/002_observation_schema.py`.

2. **Schema isolation.** All observation tables live in a dedicated
   Postgres schema `observation` (not `public`). The execution services
   are granted privileges only on `public`. Observation-ingest and
   pattern-classifier are the only services with `observation.*`
   privileges; they receive dedicated DB roles.

## Rationale
- **Different data, different lifecycle.** Raw events and aggregates are
  two different products with two different risk profiles; conflating
  them under one knob was a pre-v4.5 simplification that no longer
  holds.
- **90-day raw retention matches the DPIA commitment.** The template
  DPIA (§6) commits to 90 days; the default must mirror the
  commitment, not be a conservative value that customers drift upward
  from.
- **365-day aggregated retention supports the Govern cadence.**
  Quarterly works-council reports (Betriebsvereinbarung §8) require
  year-over-quarter comparisons; anything <365 days breaks that cadence.
- **Schema isolation is the cheap, high-value defence.** It defends
  against entire classes of bugs ("service X accidentally joined against
  observation_events") with zero runtime cost. Row-level security
  complements it but doesn't replace it — a principle-of-least-privilege
  approach uses both.
- **A CHECK on `proposals.employee_count >= 3`** mirrors the
  application-level aggregation gate in the database. If someone
  bypasses the classifier code path, the DB rejects the write. Defence
  in depth.

## Consequences
- **Existing tenant rows need a backfill** from `retention_days` into
  `audit_retention_days`. Migration 002 handles this.
- **Operational playbooks that mention `retention_days` must be
  updated.** Tracked in the infra runbook.
- **Two new cron jobs** are required: raw-observation purge (90 days)
  and aggregated-pattern purge (365 days). Both belong in the
  observation-ingest service — added to its TODO list.
- **Service DB roles multiply.** Each service now has a narrower,
  purpose-built role. Documented in
  `services/control-plane/migrations/versions/002_observation_schema.py`
  comments.
- **Cross-schema queries are explicit.** Any service that legitimately
  needs both (e.g. the Propose layer joining proposals against the
  tenant audit log) must qualify table names with the schema. This is a
  feature — it makes the boundary visible in code review.

## Alternatives and why they were rejected
- *Keep a single `retention_days`* — breaks the DPIA commitment or the
  Govern cadence, depending on which value is chosen.
- *Row-level security only, same schema* — RLS is good but insufficient;
  a grant oversight still exposes the table.
- *Separate database entirely* — operational overhead (separate
  connection pool, separate backup window, separate migration tooling)
  doesn't earn its keep at MVP scale.

## References
- Business Plan v4.5 §11A.5 (privacy by design), §14 (compliance scope).
- [services/control-plane/migrations/versions/002_observation_schema.py](../../services/control-plane/migrations/versions/002_observation_schema.py)
- [docs/security/dpia-observation-layer.md](../security/dpia-observation-layer.md)
- [docs/security/betriebsvereinbarung-template.md](../security/betriebsvereinbarung-template.md)
- ADR [008](008-hdbscan-pattern-classifier.md) (the aggregation gate is mirrored there).
