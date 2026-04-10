# Data Flow Diagram

## System Boundary

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ant Automations Platform                      │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ Control   │    │ Planner  │    │ Workers  │    │ Vision   │      │
│  │ Plane     │───▶│ (Graph)  │───▶│ (Exec)   │    │ (Model)  │      │
│  │ API       │    │          │    │          │    │          │      │
│  └─────┬────┘    └────┬─────┘    └────┬─────┘    └──────────┘      │
│        │              │               │                              │
│        ▼              ▼               ▼                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│  │ Postgres │    │ NATS     │    │Connectors│                       │
│  │ (State)  │    │ (Events) │    │(Entra/SN)│                       │
│  └──────────┘    └──────────┘    └────┬─────┘                       │
│                                       │                              │
└───────────────────────────────────────┼──────────────────────────────┘
                                        │ TLS
                                        ▼
                               ┌──────────────────┐
                               │ External Systems  │
                               │ (Entra ID, SNOW)  │
                               └──────────────────┘
```

## Data Flows

| # | Source | Destination | Data Type | Protocol | Encryption |
|---|--------|-------------|-----------|----------|------------|
| 1 | User/Admin | Control Plane | Auth tokens, config | HTTPS (TLS 1.3) | In transit |
| 2 | Control Plane | Postgres | Tenant config, RBAC | mTLS | At rest + in transit |
| 3 | Control Plane | Planner | Workflow triggers | mTLS | In transit |
| 4 | Planner | NATS | Workflow events | TLS | In transit |
| 5 | Planner | Workers | Task assignments | Via NATS (TLS) | In transit |
| 6 | Workers | Connectors | Action requests | mTLS | In transit |
| 7 | Connectors | Entra ID | User operations | HTTPS (TLS 1.3) | In transit |
| 8 | Connectors | ServiceNow | Ticket operations | HTTPS (TLS 1.3) | In transit |
| 9 | All Services | Postgres | Audit events | mTLS | At rest + in transit |
| 10 | All Services | OTel Collector | Traces, metrics | gRPC (TLS) | In transit |
