# Ant Automations

Enterprise automation platform that **watches** how operational teams work, **learns** the repetitive
patterns they do not notice, **proposes** automations with estimated savings, and — only after a
human approves — **executes** them under enterprise-grade governance.

Product ladder: **Watch → Learn → Propose → Execute → Govern.**

> Aligned to Business Plan v4.5. The previous "builds and governs a digital workforce" framing (v4.4)
> was replaced with the observation-first narrative in v4.5 §1 and Appendix D.

## The Five Layers

| Layer | What it does | Key services |
|---|---|---|
| **Watch** | Lightweight desktop agent and browser extension silently capture employee interaction patterns (application switches, navigation, form submissions) — **no content**, no keystrokes, no screen recording. | [`clients/desktop-agent`](clients/desktop-agent) (Tauri), [`clients/browser-extension`](clients/browser-extension) (Chrome MV3), [`services/observation-ingest`](services/observation-ingest) |
| **Learn** | Pattern classifier mines recurring multi-step sequences out of normalised event streams, clusters them into workflow candidates, scores feasibility and savings. | [`services/pattern-classifier`](services/pattern-classifier) |
| **Propose** | Discovered patterns are surfaced to team leads with frequency, estimated savings, and risk assessment. Nothing automates until a human accepts a proposal. | [`services/control-plane`](services/control-plane) (proposal review API — in progress) |
| **Execute** | Accepted proposals are compiled into LangGraph workflow graphs, executed through API-first connectors with verification steps. | [`services/planner`](services/planner), [`services/connectors`](services/connectors), [`services/workers`](services/workers) |
| **Govern** | Policy engine, risk-based approval chains, immutable audit trail, tenant isolation, RBAC. | [`services/control-plane`](services/control-plane) |

## Repository Structure

```
├── clients/
│   ├── desktop-agent/       # Tauri (Rust + WebView) — Watch layer, employee machines
│   └── browser-extension/   # Chrome Manifest V3 — Watch layer, SaaS apps
├── services/
│   ├── observation-ingest/  # Watch: NATS consumer + event normaliser (port 8006)
│   ├── pattern-classifier/  # Learn: sequence mining + HDBSCAN clustering (port 8007)
│   ├── planner/             # Execute: LangGraph workflow orchestration (port 8001)
│   ├── connectors/          # Execute: connector framework + Entra ID + ServiceNow (port 8002)
│   ├── control-plane/       # Govern: admin console, tenants, RBAC, safety layer (port 8003)
│   ├── workers/             # Execute: task execution pool (port 8004)
│   └── vision/              # Execute: SGLang model serving for document understanding (port 8005)
├── libs/
│   └── observability/       # Shared OTel instrumentation and metrics
├── infrastructure/
│   └── monitoring/          # Grafana dashboards, Prometheus, OTel collector configs
├── docs/
│   ├── architecture.md      # Platform architecture (Watch → Learn → Propose → Execute → Govern)
│   ├── adr/                 # Architecture Decision Records
│   └── security/            # Security + compliance package (DPIA, works-council templates, etc.)
├── docker-compose.yml       # Full stack including observation and pattern-classifier services
└── .github/workflows/       # CI: lint, test, Docker build per service
```

## Quick Start

```bash
# Start all services and infrastructure
docker-compose up --build

# Execute + Govern services
curl http://localhost:8001/healthz  # planner
curl http://localhost:8002/healthz  # connectors
curl http://localhost:8003/healthz  # control-plane
curl http://localhost:8004/healthz  # workers
curl http://localhost:8005/healthz  # vision

# Watch + Learn services (scaffolded in v4.5)
curl http://localhost:8006/healthz  # observation-ingest
curl http://localhost:8007/healthz  # pattern-classifier
```

## Status by Layer (v4.5 alignment)

| Layer | State | Notes |
|---|---|---|
| Watch | **Scaffold** | Tauri desktop agent and Chrome MV3 extension emit the observation event schema; ingest service normalises into NATS JetStream. See the Watch services README files for next-step TODOs. |
| Learn | **Scaffold + classifier contract** | Service wiring, HDBSCAN dependency, API shape, and the **min-3-employee aggregation gate** as a hard architectural constraint (see [ADR 008](docs/adr/008-hdbscan-pattern-classifier.md)). Sequence mining and embedding pipeline stubbed. |
| Propose | **Schema ready** | Migration `002_observation_schema` adds `workflow_candidates`, `proposals`, `proposal_decisions`, `observation_events`, `observed_sequences`. Admin console review API pending. |
| Execute | **Production-track** | LangGraph workflows, Entra ID + ServiceNow connectors, worker pool, supervised/observation/autonomous modes. |
| Govern | **Production-track** | RBAC, approval chains, immutable audit trail, declarative policy engine, tenant isolation. |

## Key Workflows

### IT Access Provisioning (Joiner/Mover/Leaver)
- Automated user lifecycle management via Entra ID connector
- Department-based templates (engineering, finance, IT-ops, sales)
- Three execution modes: observation, supervised, autonomous

### Ticket Triage and Routing
- Automated ticket categorisation and priority assessment via ServiceNow connector
- Intelligent routing to appropriate support teams
- Knowledge base search for suggested resolutions
- SLA tracking and escalation

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Desktop observation agent | Tauri (Rust + WebView) |
| Browser observation extension | Chrome Extension Manifest V3 |
| Pattern classifier | Qwen3-30B-A3B embeddings + HDBSCAN clustering |
| Orchestration | LangGraph |
| Planner model | Qwen3-30B-A3B (MoE) |
| Vision model | Phi-4-reasoning-vision-15B |
| Model serving | SGLang |
| API framework | FastAPI |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Event bus | NATS (JetStream) |
| Object storage | MinIO |
| Observability | OpenTelemetry, Prometheus, Grafana |
| CI/CD | GitHub Actions |

## Architecture Decision Records

- [ADR 001](docs/adr/001-langgraph-orchestration.md) — LangGraph for workflow orchestration
- [ADR 002](docs/adr/002-sglang-serving.md) — SGLang for model serving
- [ADR 003](docs/adr/003-nats-event-bus.md) — NATS as default event bus
- [ADR 004](docs/adr/004-qwen3-planner-model.md) — Qwen3-30B-A3B planner model
- [ADR 005](docs/adr/005-phi4-vision-model.md) — Phi-4-reasoning-vision-15B vision model
- [ADR 006](docs/adr/006-tauri-desktop-agent.md) — Tauri for the desktop observation agent
- [ADR 007](docs/adr/007-chrome-mv3-extension.md) — Chrome Manifest V3 for the browser extension
- [ADR 008](docs/adr/008-hdbscan-pattern-classifier.md) — HDBSCAN + Qwen3 embeddings for the pattern classifier
- [ADR 009](docs/adr/009-observation-data-retention.md) — Split retention for observation vs audit data

## Security & Compliance

See [docs/security/](docs/security/) for the enterprise security package:

- [Architecture brief](docs/security/architecture-brief.md)
- [Data flow diagram](docs/security/data-flow-diagram.md)
- [Data retention policy](docs/security/data-retention-policy.md)
- [Betriebsvereinbarung template (DE works-council agreement)](docs/security/betriebsvereinbarung-template.md) — **required before any DACH pilot**
- [Instemmingsverzoek template (NL works-council consent)](docs/security/instemmingsverzoek-template.md) — **required before any NL pilot**
- [DPIA — observation layer](docs/security/dpia-observation-layer.md)
- [Employee privacy notice template](docs/security/employee-privacy-notice.md)

## For contributors

This repo was restructured in April 2026 to align with Business Plan v4.5. If you were familiar with
the prior structure:

- **"Digital workforce" framing is gone.** The product is not "build agents and govern them." The
  product is "observe work, discover what is repetitive, propose automations, execute under
  governance." All user-facing copy should reflect this ladder.
- **Watch and Learn are first-class layers**, not an internal feature of Execute. See `clients/` and
  the two new services under `services/`.
- **Observation data is not audit data.** It lives in a separate Postgres schema, has its own
  retention policy (default 90 days raw / 365 days aggregated), and is subject to an
  architectural constraint that patterns must be observed across **at least 3 employees** before
  they are surfaced as proposals. This is enforced in code, not configuration — see
  [ADR 008](docs/adr/008-hdbscan-pattern-classifier.md).
- **Works-council engagement is part of the pilot sales process**, not a post-hoc legal review.
  Templates are committed; do not deploy the Watch layer to a DACH customer without them.
