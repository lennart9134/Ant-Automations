# Ant Automations — Platform Architecture

## Overview

Ant Automations builds and governs a digital workforce of specialised AI agents for enterprise environments. The platform automates IT operations workflows (access provisioning, ticket triage, compliance) with policy-driven governance, human-in-the-loop approval chains, and full audit trails.

## Architecture Layers

### 1. Orchestration Layer — LangGraph

- **Service**: `services/planner`
- **Role**: Stateful multi-step workflow execution
- **Model**: Qwen3-30B-A3B (planner/reasoning)
- **Pattern**: Each workflow is a LangGraph `StateGraph` with typed state, conditional routing, and approval gates
- **Workflows**: Access provisioning (joiner/mover/leaver), ticket triage and routing

### 2. Model Serving — SGLang

- **Service**: `services/vision`
- **Models**:
  - Planner: Qwen3-30B-A3B (language reasoning, action planning)
  - Vision: Phi-4-reasoning-vision-15B (document understanding, form extraction)
- **Runtime**: SGLang for high-throughput batched inference with prefix caching

### 3. Connector Framework

- **Service**: `services/connectors`
- **Pattern**: `BaseConnector` abstract class with `authenticate()`, `execute()`, `healthcheck()`
- **Connectors**:
  - **Entra ID** — User lifecycle, group management, role assignment via Microsoft Graph API
  - **ServiceNow** — Incident management, ticket triage, knowledge base search
- **Features**: Scoped service identities, built-in audit trail generation, permission model per connector

### 4. Safety Layer (Governance)

- **Location**: `services/control-plane/src/safety/`
- **Components**:
  - **Approval chains** — Risk-based routing: low (auto-approve), medium (single approver), high (multi-approver with escalation)
  - **Audit trail** — Immutable structured logging with 10 event types, SIEM-exportable
  - **Policy engine** — Declarative rules evaluated per action, first-match-wins with priority ordering

### 5. Control Plane

- **Service**: `services/control-plane`
- **Components**:
  - **Admin console API** — Dashboard, connector status, worker utilization, audit log viewer
  - **Tenant configuration** — Multi-tenant settings: workflow templates, connector configs, approval policies
  - **RBAC** — Four roles: platform_admin, tenant_admin, operator, viewer

### 6. Data Layer

- **Postgres** — Workflow state, approval records, audit log, tenant configuration
- **Redis** — Job queues, caching, session state
- **NATS** (JetStream) — Event bus for decoupled service communication
- **MinIO** — Object storage for documents and artifacts

### 7. Observability

- **Library**: `libs/observability/`
- **Stack**: OpenTelemetry → Collector → Prometheus + Grafana
- **Metrics**: 14 platform-wide metrics (workflow, step, connector, model, approval)
- **Dashboards**: Platform overview with workflow success rate, connector health, model latency, approval turnaround

### 8. Execution Workers

- **Service**: `services/workers`
- **Role**: Task execution pool consuming from NATS, executing connector actions and tool calls

## Deployment Models

1. **Private Cloud** — Customer-managed K8s cluster, all components deployed as containers
2. **Managed VPC** — Ant Automations-operated infrastructure within customer's cloud account
3. **On-Premises** — Air-gapped deployment with local model serving and no external dependencies

## Service Ports

| Service         | Port |
|----------------|------|
| Planner        | 8001 |
| Connectors     | 8002 |
| Control Plane  | 8003 |
| Workers        | 8004 |
| Vision         | 8005 |
| Postgres       | 5432 |
| Redis          | 6379 |
| NATS           | 4222 |
| MinIO          | 9000 |
| OTel Collector | 4317 |
| Prometheus     | 9090 |
| Grafana        | 3000 |

## Quick Start

```bash
docker-compose up --build
```

All services start with health endpoints at `GET /healthz`.
