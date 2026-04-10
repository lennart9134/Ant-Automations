# Ant Automations

Enterprise AI platform that builds and governs a digital workforce of specialised AI agents for enterprise environments. Policy-driven governance, human-in-the-loop approval chains, full audit trails, and private deployment with open-weight models.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full platform architecture overview.

**Key components:**
- **LangGraph orchestration** — Stateful multi-step workflows with approval gates
- **Connector framework** — Pluggable business-system integrations (Entra ID, ServiceNow)
- **Safety layer** — Risk-based approval chains, immutable audit trail, declarative policy engine
- **Control plane** — Admin console API, multi-tenant config, RBAC
- **Observability** — OpenTelemetry + Prometheus + Grafana with 14 platform metrics

## Repository Structure

```
├── services/
│   ├── planner/          # LangGraph workflow orchestration (port 8001)
│   ├── connectors/       # Connector framework + Entra ID + ServiceNow (port 8002)
│   ├── control-plane/    # Admin console, tenant config, RBAC, safety layer (port 8003)
│   ├── workers/          # Task execution pool (port 8004)
│   └── vision/           # SGLang model serving for document understanding (port 8005)
├── libs/
│   └── observability/    # Shared OTel instrumentation and metrics
├── infrastructure/
│   └── monitoring/       # Grafana dashboards, Prometheus, OTel collector configs
├── docs/
│   ├── architecture.md   # Platform architecture overview
│   ├── adr/              # Architecture Decision Records
│   └── security/         # Security architecture, data flow, retention policy
├── docker-compose.yml    # Full stack: all services + Postgres, Redis, NATS, MinIO, monitoring
└── .github/workflows/    # CI: lint, test, Docker build per service
```

## Quick Start

```bash
# Start all services and infrastructure
docker-compose up --build

# Verify services are running
curl http://localhost:8001/healthz  # planner
curl http://localhost:8002/healthz  # connectors
curl http://localhost:8003/healthz  # control-plane
curl http://localhost:8004/healthz  # workers
curl http://localhost:8005/healthz  # vision
```

## Key Workflows

### IT Access Provisioning (Joiner/Mover/Leaver)
- Automated user lifecycle management via Entra ID connector
- Department-based templates (engineering, finance, IT-ops, sales)
- Three execution modes: observation, supervised, autonomous

### Ticket Triage and Routing
- Automated ticket categorization and priority assessment via ServiceNow connector
- Intelligent routing to appropriate support teams
- Knowledge base search for suggested resolutions
- SLA tracking and escalation

## Technology Stack

| Layer | Technology |
|-------|-----------|
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

## Engineering Decision Records

- [ADR 001](docs/adr/001-langgraph-orchestration.md) — LangGraph for workflow orchestration
- [ADR 002](docs/adr/002-sglang-serving.md) — SGLang for model serving
- [ADR 003](docs/adr/003-nats-event-bus.md) — NATS as default event bus
- [ADR 004](docs/adr/004-qwen3-planner-model.md) — Qwen3-30B-A3B planner model
- [ADR 005](docs/adr/005-phi4-vision-model.md) — Phi-4-reasoning-vision-15B vision model

## Security

See [docs/security/](docs/security/) for the enterprise security package:
- [Architecture brief](docs/security/architecture-brief.md)
- [Data flow diagram](docs/security/data-flow-diagram.md)
- [Data retention policy](docs/security/data-retention-policy.md)
