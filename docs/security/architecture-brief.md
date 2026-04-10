# Security Architecture Brief

## 1. Tenancy Isolation

- **Compute**: Each tenant's workflows execute in isolated worker pools with no shared memory
- **Data**: Tenant data is logically separated in Postgres via `tenant_id` column on all tables; row-level security (RLS) policies enforce isolation at the database layer
- **Network**: In managed VPC deployments, each tenant gets a dedicated VPC with no peering between tenants
- **Models**: Model inference contexts are isolated per request; no cross-tenant prompt leakage

## 2. Access Controls

- **RBAC**: Four-tier role model (platform_admin, tenant_admin, operator, viewer) with granular permission sets
- **Service identities**: Each connector authenticates with the minimum required permissions (least privilege)
- **API authentication**: JWT-based with short-lived tokens (15-minute expiry), refresh token rotation
- **MFA**: Required for all human users accessing the control plane

## 3. Encryption

### At Rest
- Postgres: AES-256 transparent data encryption (TDE) via cloud provider KMS
- MinIO: Server-side encryption with customer-managed keys (SSE-C)
- Redis: In-memory only; persistent data stored in Postgres

### In Transit
- All inter-service communication: mTLS with auto-rotated certificates
- External APIs: TLS 1.3 minimum
- NATS: TLS with client certificate authentication

## 4. Data Flow

```
User Input → Control Plane API (TLS) → Planner (mTLS) → Model Inference (local)
                                                        → Connector (mTLS) → External System (TLS)
                                                        → Audit Trail (Postgres, encrypted)
```

Personal data enters through:
1. Workflow triggers (user identity from IdP)
2. Connector responses (user attributes from Entra ID, ticket content from ServiceNow)

Personal data is processed in:
1. Planner service (action planning, risk assessment)
2. Worker service (action execution)

Personal data is stored in:
1. Postgres (workflow state, audit log) — encrypted at rest, RLS-isolated per tenant
2. Audit log (immutable, append-only) — retained per tenant policy

## 5. Sub-Processors

| Sub-Processor | Data Type | Residency | Retention |
|--------------|-----------|-----------|-----------|
| Customer Cloud (Private/VPC) | All workflow data | Customer-selected region | Customer-controlled |
| Model Inference (local) | Prompt/completion text | Same as compute | Request-scoped (no persistence) |
| Postgres (managed) | Workflow state, audit | Customer-selected region | Per retention policy |

## 6. Data Retention and Deletion

- **Configurable per tenant**: Retention period set in tenant configuration (default: 90 days)
- **Audit log**: Minimum 1 year retention (regulatory), maximum configurable
- **Deletion**: Tenant admin can trigger full data deletion; cascade deletes workflow state, audit entries, and stored documents
- **Right to erasure**: Personal data can be purged per individual on request via control plane API
