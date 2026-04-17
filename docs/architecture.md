# Ant Automations — Platform Architecture

## Overview

Ant Automations observes how operational teams actually work, learns which cross-system tasks are
repetitive, proposes automations with evidence, and — after a human accepts a proposal — executes
them under policy-driven governance with an immutable audit trail.

The platform is organised as a **five-stage product ladder**:

**Watch → Learn → Propose → Execute → Govern.**

Each stage is a discrete architectural concern with its own services, data model, and trust
guarantees. No stage activates without explicit customer consent. No execution happens until
observation data supports it and a human approves it.

> This document supersedes the v4.4 "digital workforce" architecture. See Business Plan v4.5 §5.

## The 9-Step Platform Loop

Per Business Plan v4.5 §5.2:

| Step | Phase | Action | Responsible service |
|---|---|---|---|
| 1 | **Watch** | Desktop agent / browser extension / API event tap captures interaction events (no content). | `clients/desktop-agent`, `clients/browser-extension`, `services/observation-ingest` |
| 2 | **Watch** | Events normalised to the unified action schema and written to the event bus. | `services/observation-ingest` |
| 3 | **Learn** | Pattern classifier extracts recurring sequences and clusters them into workflow candidates. | `services/pattern-classifier` |
| 4 | **Learn** | Frequency, duration, cost, and feasibility scores calculated per candidate. | `services/pattern-classifier` |
| 5 | **Propose** | Candidates surfaced as proposals with savings and risk; team lead accepts / rejects / defers. | `services/control-plane` |
| 6 | **Execute** | Accepted proposals compiled into LangGraph workflow graphs; planner selects actions. | `services/planner` |
| 7 | **Execute** | Execution layer performs the action via API, browser, or GUI control. | `services/connectors`, `services/workers` |
| 8 | **Govern** | Verifier step confirms the expected outcome. | `services/planner` (verifier nodes) |
| 9 | **Govern** | Audit trail written; policy rules enforced; workflow reliability score updated. | `services/control-plane` |

## Architecture Layers

### 1. Watch — Observation Layer

- **Clients**: `clients/desktop-agent` (Tauri + Rust), `clients/browser-extension` (Chrome MV3)
- **Service**: `services/observation-ingest` (port 8006)
- **Role**: Capture application switches, navigation sequences, form-submission events,
  cross-system data flows — **metadata only**. No keystroke logging, no clipboard content, no
  screen recording by default.
- **Privacy by design**: event schema is `{timestamp, actor_id, action_type, source_application,
  target_application, duration, metadata}`. Employees see a system-tray indicator; observation can
  be paused at any time. Domain allowlist and configurable scope per department.
- **Transport**: NATS JetStream, dedicated streams with a separate retention policy (see Govern).
- **Decision records**: [ADR 006](adr/006-tauri-desktop-agent.md),
  [ADR 007](adr/007-chrome-mv3-extension.md).

### 2. Learn — Pattern Classifier

- **Service**: `services/pattern-classifier` (port 8007)
- **Role**: Mine recurring sequences out of normalised event streams; cluster into workflow
  candidates; score feasibility and savings.
- **Pipeline**:
  1. Sliding-window sequence extraction (default window 20, min recurrence 5)
  2. Qwen3-30B-A3B embeddings over action sequences
  3. HDBSCAN density-based clustering to group variable-length sequences
  4. Statistical aggregation: occurrences/week, duration, FTE cost
  5. Feasibility scoring against the connector registry
- **Hard architectural constraint**: patterns must be observed across **at least 3 distinct
  employees** before they can be surfaced as proposals. Enforced in code, not configuration —
  see [ADR 008](adr/008-hdbscan-pattern-classifier.md) and §11A.5 of the business plan.
- **Minimum observation window**: 14 days before the classifier returns results; 28 days for
  production-grade confidence.

### 3. Propose — Proposal Engine

- **Location**: `services/control-plane` (proposal review endpoints)
- **Data model**: `workflow_candidates`, `proposals`, `proposal_decisions` tables (see migration
  `002_observation_schema`).
- **Review workflow**: Each proposal includes pattern description, frequency data, time-savings
  estimate, feasibility score, risk level (low/medium/high), recommended execution mode, and
  confidence score. A team lead can accept (→ workflow builder), reject (not-a-candidate), or
  defer (re-evaluate after more observation).
- **Employee-level prohibition**: no proposal can reference a single named employee. Proposals
  operate on cross-employee aggregate data only.

### 4. Execute — Orchestration & Connectors

- **Orchestration**: `services/planner` (LangGraph, port 8001) — stateful multi-step workflow
  execution with typed state, conditional routing, and approval gates.
- **Planner model**: Qwen3-30B-A3B, served by SGLang (see [ADR 004](adr/004-qwen3-planner-model.md)).
- **Vision model**: Phi-4-reasoning-vision-15B (see [ADR 005](adr/005-phi4-vision-model.md)).
- **Connectors**: `services/connectors` — `BaseConnector` abstract class with
  `authenticate()` / `execute()` / `healthcheck()`. Ships Entra ID and ServiceNow; Okta, Salesforce,
  SAP, and Jira on the roadmap.
- **Workers**: `services/workers` — task execution pool consuming from NATS, executing connector
  actions and tool calls. Supports API-first, browser (Playwright), and selective RPA.
- **Verifier nodes**: every workflow must have an explicit verifier step before it can graduate
  from observation → supervised → controlled autonomy.

### 5. Govern — Safety & Control Plane

- **Location**: `services/control-plane/src/safety/`
- **Components**:
  - **RBAC** — four roles: platform_admin, tenant_admin, operator, viewer
  - **Approval chains** — risk-based routing: low (auto-approve), medium (single approver),
    high (multi-approver with escalation)
  - **Policy engine** — declarative rules, first-match-wins with priority ordering
  - **Audit trail** — append-only `audit_events`, structured events, SIEM-exportable
  - **Tenant isolation** — middleware-enforced scoping; per-tenant workflow templates,
    connector configs, and approval policies
- **Observation governance** (new in v4.5):
  - Split retention: observation data defaults to 90 days raw / 365 days aggregated; audit
    data defaults to a longer per-tenant period (see [ADR 009](adr/009-observation-data-retention.md)).
  - Observation scope is configurable per department (minimal → application-level → action-level).
  - Employee transparency: system-tray indicator, pause capability, observation status endpoint.

## Data Layer

- **Postgres** — workflow state, approval records, audit log, tenant configuration, **and**
  observation events, observed sequences, workflow candidates, proposals, proposal decisions.
  Observation tables live in a schema (`observation.*`) that is isolated from the rest of the
  application data and has separate access grants — see migration `002_observation_schema`.
- **Redis** — job queues, caching, session state
- **NATS (JetStream)** — event bus. Two stream families:
  - Application events (workflow orchestration, approvals, execution)
  - Observation events (`observation.events.*`) with separate retention and access policy
- **MinIO** — object storage for documents, artefacts, and replay traces

## Observability

- **Library**: `libs/observability/`
- **Stack**: OpenTelemetry → Collector → Prometheus + Grafana
- **Metrics**: platform-wide metrics covering workflow, step, connector, model, approval. Watch-
  and Learn-layer metrics (observation coverage, pattern discovery rate, proposal acceptance rate,
  observation-to-pilot conversion) are in the plan and are being added as services come online.
- **Dashboards**: platform overview with workflow success rate, connector health, model latency,
  approval turnaround.

## Deployment Models

1. **Private Cloud** — default commercial path. All components deployed as containers in a
   customer-managed or Ant-operated cluster.
2. **Managed VPC** — customer's own cloud account, network-isolated.
3. **On-Premises** — air-gapped deployment with local model serving and no external dependencies.

The observation layer runs on employee machines (desktop agent + browser extension) in every
deployment model. On-prem deployments route all observation and inference traffic inside the
customer's network; no observation data leaves the customer's jurisdiction under any model.

## Service Ports

| Service         | Port | Layer |
|----------------|------|-------|
| Planner        | 8001 | Execute |
| Connectors     | 8002 | Execute |
| Control Plane  | 8003 | Govern / Propose |
| Workers        | 8004 | Execute |
| Vision         | 8005 | Execute |
| Observation Ingest | 8006 | Watch |
| Pattern Classifier | 8007 | Learn |
| Postgres       | 5432 | Data |
| Redis          | 6379 | Data |
| NATS           | 4222 | Data |
| MinIO          | 9000 | Data |
| OTel Collector | 4317 | Observability |
| Prometheus     | 9090 | Observability |
| Grafana        | 3000 | Observability |

## Quick Start

```bash
docker-compose up --build
```

All services expose `GET /healthz`.

## Architectural Principles

Per Business Plan v4.5 §5.1:

1. **Observe first, execute later.** The platform earns execution rights through evidence, not
   configuration. No automation runs until observation data supports it and a human approves it.
2. **APIs first.** Where a business system offers a reliable API, the platform uses that route
   over GUI manipulation.
3. **Least privilege by design.** Observation captures action patterns, not content. Execution
   workers use scoped service identities, not broad human credentials.
4. **Human approval gates** for new or high-risk automations. Autonomy expands only when evidence
   supports it.
5. **Verify every action.** Execution success is proven through API responses or post-action
   checks — never assumed.
6. **Trace every action.** Inputs, model decisions, tools called, outputs, and final state are
   logged with correlation IDs for full replay.
7. **Minimum-aggregation for observation.** Patterns attributable to a single named employee must
   never be surfaced. Enforced in code (3-employee gate) as well as in policy.
