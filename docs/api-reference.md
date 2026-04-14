# Ant Automations — API Reference

All services expose REST APIs via FastAPI. Every service includes a `GET /healthz` endpoint for liveness checks.

Base URLs (local development):

| Service       | Base URL               |
|--------------|------------------------|
| Planner      | `http://localhost:8001` |
| Connectors   | `http://localhost:8002` |
| Control Plane| `http://localhost:8003` |
| Workers      | `http://localhost:8004` |
| Vision       | `http://localhost:8005` |

---

## Planner Service (port 8001)

The planner service orchestrates multi-step workflows using LangGraph. Workflow actions are dispatched asynchronously via NATS to the workers service.

### Run a Workflow

```
POST /api/v1/workflows/{workflow_name}/run
```

Triggers a workflow execution through the LangGraph engine. If shadow mode is disabled and NATS is connected, connector actions produced by the workflow are published to the `tasks.connector_action` subject.

**Path parameters:**

| Parameter       | Type   | Description |
|----------------|--------|-------------|
| `workflow_name` | string | Workflow identifier: `access_provisioning` or `ticket_triage` |

**Request body** (JSON):

For `access_provisioning`:
```json
{
  "employee_name": "Jane Smith",
  "email": "jane.smith@company.com",
  "department": "engineering",
  "event_type": "joiner",
  "execution_mode": "supervised"
}
```

| Field            | Type   | Required | Description |
|-----------------|--------|----------|-------------|
| `employee_name` | string | yes      | Full name of the employee |
| `email`         | string | yes      | Corporate email address |
| `department`    | string | yes      | One of: `engineering`, `finance`, `it-ops`, `sales` |
| `event_type`    | string | yes      | Lifecycle event: `joiner`, `mover`, or `leaver` |
| `execution_mode`| string | no       | `observation` (log only), `supervised` (require approval), `autonomous` (auto-execute). Default: `supervised` |

For `ticket_triage`:
```json
{
  "ticket_id": "INC0010042",
  "short_description": "VPN not connecting",
  "description": "User reports VPN client shows error code 0x800...",
  "caller": "john.doe@company.com"
}
```

**Response:**
```json
{
  "workflow": "access_provisioning",
  "run_id": "uuid",
  "status": "completed",
  "shadow": false
}
```

| Field      | Type    | Description |
|-----------|---------|-------------|
| `workflow`| string  | Echo of the requested workflow name |
| `run_id`  | string  | Unique execution identifier (UUID) |
| `status`  | string  | Execution status: `completed`, `failed`, `pending_approval` |
| `shadow`  | boolean | `true` if executed in shadow mode (no side effects) |

### Get Shadow Log

```
GET /api/v1/shadow-log
```

Returns the shadow mode execution log — shows what the system would have done without actually executing connector actions.

**Response:**
```json
{
  "entries": [
    {
      "workflow": "access_provisioning",
      "run_id": "uuid",
      "timestamp": "2026-04-14T10:00:00Z",
      "planned_actions": [...]
    }
  ],
  "total": 1
}
```

---

## Connectors Service (port 8002)

Manages the lifecycle and execution of business-system connectors.

### List Connectors

```
GET /api/v1/connectors
```

Returns all registered connectors with their status and supported actions.

**Response:**
```json
[
  {
    "name": "entra_id",
    "status": "healthy",
    "actions": [
      "create_user", "disable_user", "delete_user", "get_user",
      "list_users", "assign_group", "remove_group", "list_groups",
      "assign_role", "revoke_all_sessions"
    ]
  },
  {
    "name": "servicenow",
    "status": "healthy",
    "actions": [
      "create_incident", "update_incident", "assign_incident",
      "get_incident", "list_incidents", "add_comment",
      "categorize_incident", "search_knowledge_base",
      "get_sla_status", "escalate_incident"
    ]
  }
]
```

### Execute Connector Action

```
POST /api/v1/connectors/{connector_name}/execute
```

Execute an action against a specific connector.

**Path parameters:**

| Parameter        | Type   | Description |
|-----------------|--------|-------------|
| `connector_name` | string | Connector identifier: `entra_id` or `servicenow` |

**Request body:**
```json
{
  "action": "create_user",
  "parameters": {
    "email": "jane.smith@company.com",
    "display_name": "Jane Smith",
    "department": "engineering"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "azure-object-id",
    "email": "jane.smith@company.com",
    "status": "created"
  },
  "error": null
}
```

#### Entra ID Actions

| Action                | Parameters | Description |
|----------------------|------------|-------------|
| `create_user`        | `email`, `display_name`, `department`, `temp_password` (optional) | Create a user in Azure AD |
| `disable_user`       | `user_id` | Disable a user account |
| `delete_user`        | `user_id` | Permanently delete a user |
| `get_user`           | `user_id` | Retrieve user details |
| `list_users`         | `limit` (optional, default 100) | List users in the directory |
| `assign_group`       | `user_id`, `group` (group ID) | Add user to a security group |
| `remove_group`       | `user_id`, `group` (group ID) | Remove user from a group |
| `list_groups`        | `limit` (optional, default 100) | List available groups |
| `assign_role`        | `user_id`, `role` (role definition ID) | Assign a directory role |
| `revoke_all_sessions`| `user_id` | Revoke all active sign-in sessions |

#### ServiceNow Actions

| Action                  | Parameters | Description |
|------------------------|------------|-------------|
| `create_incident`      | `short_description` | Create a new incident |
| `update_incident`      | `sys_id`, plus fields to update | Update incident fields |
| `assign_incident`      | `sys_id`, `assigned_to`, `assignment_group` | Assign/reassign an incident |
| `get_incident`         | `sys_id` | Retrieve incident details |
| `list_incidents`       | (none) | List incidents |
| `add_comment`          | `sys_id`, `comment` | Add a work note or comment |
| `categorize_incident`  | `sys_id`, `category`, `subcategory` | Set incident category |
| `search_knowledge_base`| `query` | Search KB articles |
| `get_sla_status`       | `sys_id` | Get SLA compliance status |
| `escalate_incident`    | `sys_id`, `new_priority` (optional, default "2") | Escalate incident priority |

---

## Control Plane (port 8003)

Admin console, tenant configuration, RBAC, approval chains, and audit trail. All endpoints under `/api/v1/` require authentication via the RBAC middleware.

### Middleware Stack

Requests pass through these middleware layers in order:

1. **CORS** — Handles preflight requests (configurable origins via `CORS_ORIGINS` env var)
2. **Rate limiting** — Protects against brute-force attacks
3. **RBAC** — Authenticates the request and sets user context with one of four roles: `platform_admin`, `tenant_admin`, `operator`, `viewer`
4. **Tenant isolation** — Scopes every request to the authenticated user's tenant

### Admin Dashboard

```
GET /api/v1/admin/dashboard
```

Aggregated overview: workflow counts, pending approvals, and recent audit log entries.

**Response:**
```json
{
  "workflows": {
    "running": 0,
    "completed_today": 0,
    "failed_today": 0
  },
  "approvals": {
    "pending": 2,
    "approved_today": 5,
    "denied_today": 1
  },
  "recent_audit": [
    {
      "id": "uuid",
      "event_type": "connector_action",
      "action": "create_user"
    }
  ]
}
```

### Connector Status

```
GET /api/v1/admin/connectors/status
```

Returns health status of all registered connectors.

### Worker Utilization

```
GET /api/v1/admin/workers/utilization
```

Returns worker pool metrics: total, active, queued tasks, utilization percentage.

### Audit Log

```
GET /api/v1/admin/audit?limit=50&offset=0
```

Paginated audit log viewer.

**Query parameters:**

| Parameter | Type | Default | Description |
|----------|------|---------|-------------|
| `limit`  | int  | 50      | Page size |
| `offset` | int  | 0       | Number of entries to skip |

**Response:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "timestamp": "2026-04-14T10:00:00Z",
      "event_type": "connector_action",
      "action": "create_user",
      "resource": "user:jane@company.com",
      "outcome": "success"
    }
  ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

### Create Approval Request

```
POST /api/v1/approvals/
```

Create a new approval request routed through the risk-based approval chain.

**Request body:**
```json
{
  "workflow_run_id": "uuid",
  "action_description": "Create user account for jane.smith@company.com",
  "risk_level": "medium",
  "requested_by": "system",
  "approvers": ["admin-1", "admin-2"]
}
```

| Field                | Type     | Description |
|---------------------|----------|-------------|
| `workflow_run_id`   | string   | ID of the workflow run that triggered this approval |
| `action_description`| string   | Human-readable description of the action |
| `risk_level`        | string   | `low` (auto-approve), `medium` (single approver), `high` (multi-approver with escalation) |
| `requested_by`      | string   | Identity of the requester |
| `approvers`         | string[] | Ordered list of approver IDs |

**Response:**
```json
{
  "approval_id": "uuid",
  "status": "pending",
  "workflow_run_id": "uuid",
  "risk_level": "medium"
}
```

### Get Approval Details

```
GET /api/v1/approvals/{approval_id}
```

Returns the approval request with its decision chain.

### Submit Approval Decision

```
POST /api/v1/approvals/{approval_id}/decide
```

**Request body:**
```json
{
  "approved": true,
  "comment": "Verified with HR — new hire confirmed"
}
```

**Response:**
```json
{
  "approval_id": "uuid",
  "status": "approved",
  "comment": "Verified with HR — new hire confirmed"
}
```

### List Pending Approvals

```
GET /api/v1/approvals/?status=pending
```

Returns all approval requests matching the given status filter.

---

## Health Check (all services)

```
GET /healthz
```

Every service exposes this endpoint. The control plane includes dependency checks:

```json
{
  "status": "ok",
  "service": "control-plane",
  "checks": {
    "postgres": true,
    "redis": true
  }
}
```

Status values: `ok` (all dependencies healthy) or `degraded` (one or more dependencies down).

---

## Error Handling

All endpoints return standard HTTP status codes. Connector execution errors are returned in the response body:

```json
{
  "success": false,
  "data": {},
  "error": "Graph API 403: Insufficient privileges to complete the operation"
}
```

## Authentication

The control plane uses RBAC middleware for authentication. Include credentials in request headers as configured for your deployment. The RBAC system defines four roles with increasing privileges:

| Role            | Capabilities |
|----------------|-------------|
| `viewer`       | Read-only access to dashboards and audit logs |
| `operator`     | Execute workflows, view approval status |
| `tenant_admin` | Manage tenant configuration, approve requests |
| `platform_admin`| Full access including cross-tenant operations |
