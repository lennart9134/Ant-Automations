# Ant Automations — Live Demo Walkthrough

**Audience**: Design-partner prospects (IT Directors, Heads of IT Operations, CISOs)
**Duration**: 25–30 minutes
**Prerequisites**: Docker Desktop running, ports 3000/8001-8005/5432/9090 free

---

## Setup (before the call)

```bash
# Start the full demo environment with seed data
docker-compose -f docker-compose.demo.yml up -d

# Verify all services are healthy (wait ~60s for startup)
docker-compose -f docker-compose.demo.yml ps

# Expected: all services "Up (healthy)" except demo-seed which exits after seeding
```

**Service URLs for the demo**:
| Service | URL | Credentials |
|---------|-----|-------------|
| Control Plane API | http://localhost:8003/docs | — |
| Connectors API | http://localhost:8002/docs | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| NATS Monitor | http://localhost:8222 | — |

---

## Part 1: Platform Overview (5 min)

### Talking points
- "Ant Automations eliminates manual operational work between enterprise systems"
- "We connect to your existing tools — Entra ID, ServiceNow, SAP — and learn your workflows"
- "Everything runs on-prem or in your VPC. No data leaves your infrastructure."

### Show: Architecture
Open the Connectors API docs:
```
http://localhost:8002/docs
```

**Demo steps**:
1. Show `GET /connectors` — list available connectors (Entra ID, ServiceNow)
2. Show `GET /connectors/entra_id/actions` — 10 supported identity operations
3. Show `GET /connectors/entra_id/permissions` — scoped Microsoft Graph permissions
4. Emphasize: "Each connector declares exactly what permissions it needs — principle of least privilege"

---

## Part 2: IT Access Provisioning — Joiner Flow (10 min)

### Scenario
> "Jane Doe is joining ACME Corp as a new engineer. HR triggers the joiner event.
> The platform plans her provisioning, requests approval, and executes via Entra ID."

### Show: Pre-seeded approval waiting for decision

**Step 2a — View the pending approval**:
```bash
curl -s http://localhost:8003/healthz | python3 -m json.tool

# Query the audit trail for the joiner workflow
curl -s "http://localhost:8003/docs"
```

Open the Control Plane Swagger UI at `http://localhost:8003/docs` and demonstrate:

1. **Audit trail** — `GET /audit/events?correlation_id=demo-joiner-001`
   - Show the workflow started, actions planned, approval requested
   - "Every step is logged immutably — this is your compliance audit trail"

2. **Pending approval** — `GET /approvals?state=pending`
   - Show the approval for Jane's account creation
   - "Two approvers required: engineering manager and IT admin"
   - "The workflow is paused here — nothing happens without human sign-off"

3. **Approval decision** — `POST /approvals/{id}/decide`
   - Approve the request
   - "Now the platform will execute the planned actions via the Entra ID connector"

### Key messages
- Three execution modes: **Observation** (log only) → **Supervised** (human approval) → **Autonomous** (low-risk auto-execute)
- "You start in observation mode. The platform shows you what it *would* do. When you trust it, you promote to supervised."
- Risk-tiered approval: low-risk actions (group assignments) can auto-execute; high-risk (account creation) always requires approval

---

## Part 3: Leaver Flow — Already Executed (5 min)

### Scenario
> "Bob Smith has left the company. The leaver workflow has already been approved and executed."

### Show: Completed workflow with full audit trail

```bash
# View the completed leaver workflow audit trail
# In Swagger UI: GET /audit/events?correlation_id=demo-leaver-001
```

Walk through the timeline:
1. Workflow started (3 hours ago)
2. Actions planned: disable account, revoke sessions, remove from 3 groups
3. Security team lead approved (with comment: "Verified with HR")
4. Connector executed: account disabled via Entra ID
5. Connector executed: sessions revoked
6. Verification passed: all planned actions confirmed executed
7. Workflow completed

### Key messages
- "The audit trail shows exactly who approved what, when, and why"
- "Every connector call is recorded with the target system response"
- "This is your GDPR Article 30 processing record, generated automatically"

---

## Part 4: ServiceNow Ticket Triage (5 min)

### Scenario
> "A high-priority ticket comes in: VPN gateway is down for the EMEA office."

### Show: Triage result in audit trail

```bash
# In Swagger UI: GET /audit/events?correlation_id=demo-triage-001
```

Walk through:
1. Ticket received: "VPN gateway down for EMEA office"
2. Auto-categorized: **infrastructure** (keyword match: "down", "gateway")
3. Priority assessed: **critical** (P1 — keyword: "down")
4. Routed to: **infra-ops** team
5. SLA set: **1 hour** response time

### Key messages
- "No human needed to triage obvious tickets — the platform handles classification and routing"
- "Your L1 support team focuses on complex issues, not ticket shuffling"
- "The routing table is configurable per tenant — your rules, our execution"

---

## Part 5: Shadow Mode / Observation (3 min)

### Scenario
> "Globex GmbH is evaluating the platform. They're running in observation mode — zero side effects."

### Show: Observation-mode audit entries

```bash
# In Swagger UI: GET /audit/events?tenant_id=globex-gmbh
```

Walk through:
1. Joiner event for Anna Mueller in Finance
2. Platform planned 8 provisioning actions
3. **No actions executed** — observation mode logged what *would* happen
4. Zero side effects recorded

### Key messages
- "This is how every customer starts — zero risk, full visibility"
- "You see exactly what the platform would do before enabling execution"
- "When ready, promote individual workflow types to supervised mode"

---

## Part 6: Observability & Compliance (3 min)

### Show: Grafana dashboard
Open `http://localhost:3000` → Platform Overview dashboard

Point out:
- Workflow execution counts and success rates
- Connector call latency and error rates
- Approval chain SLA compliance
- Per-tenant activity breakdown

### Show: SIEM export capability
- "All audit events can be exported in JSON, CEF, or Splunk HEC format"
- "Plug into your existing SIEM — Splunk, Sentinel, Elastic — with zero custom integration"

---

## Closing (2 min)

### Key differentiators to reiterate
1. **On-prem / air-gapped** — your data never leaves your infrastructure
2. **Human-in-the-loop** — approval gates on every high-risk action
3. **Immutable audit trail** — GDPR and EU AI Act compliant by design
4. **Observation-first** — see before you trust, trust before you automate
5. **Open connectors** — extend to any system with a REST API

### Call to action
> "We'd like to run a 4-week design-partner pilot. We deploy observation mode on your IT provisioning
> workflow, and within 2 weeks you'll see the actions the platform would take. No risk, no disruption.
> Interested?"

---

## Troubleshooting

**Services not starting?**
```bash
docker-compose -f docker-compose.demo.yml logs planner
docker-compose -f docker-compose.demo.yml logs control-plane
```

**Seed data not loaded?**
```bash
docker-compose -f docker-compose.demo.yml logs demo-seed
# Re-run manually:
docker-compose -f docker-compose.demo.yml run demo-seed
```

**Reset everything between demos?**
```bash
./demo/reset.sh
```
