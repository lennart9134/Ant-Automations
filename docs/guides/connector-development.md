# Connector Development Guide

How to build a new connector for the Ant Automations platform.

## Architecture

Every connector extends `BaseConnector` (defined in `services/connectors/src/framework/base.py`) and implements three methods:

```python
class BaseConnector(ABC):
    name: str = ""
    status: ConnectorStatus = ConnectorStatus.NOT_CONFIGURED
    supported_actions: tuple[str, ...] = ()
    required_permissions: tuple[PermissionScope, ...] = ()

    async def authenticate(self, credentials: dict[str, str]) -> bool: ...
    async def execute(self, action: str, parameters: dict[str, Any]) -> ConnectorResult: ...
    async def healthcheck(self) -> ConnectorStatus: ...
```

The framework provides:
- **Audit trail generation** via `_create_audit_entry()` — called in your `execute()` method
- **Permission declaration** via `PermissionScope` — documents what the connector requires from the target system
- **Status tracking** via `ConnectorStatus` — `healthy`, `degraded`, `unavailable`, `not_configured`
- **Standardized results** via `ConnectorResult` — wraps success/error with optional audit entry

## Quick Start

### 1. Create the connector package

```
services/connectors/src/connectors/
└── my_system/
    ├── __init__.py
    └── connector.py
```

### 2. Implement the connector

```python
"""My System connector — brief description of what it integrates with."""

from __future__ import annotations
from typing import Any

from ...framework.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    PermissionScope,
)


class MySystemConnector(BaseConnector):
    name = "my_system"
    supported_actions = (
        "list_items",
        "create_item",
    )
    required_permissions = (
        PermissionScope("items.read", "Read items"),
        PermissionScope("items.write", "Create and update items"),
    )

    def __init__(self) -> None:
        self._token: str | None = None

    async def authenticate(self, credentials: dict[str, str]) -> bool:
        """Authenticate with the target system.

        Expected credentials:
            api_url: Base URL of the API
            api_key: API key or OAuth client secret
        """
        api_url = credentials.get("api_url")
        api_key = credentials.get("api_key")

        if not all([api_url, api_key]):
            # Stub mode for local development
            self._token = "stub"
            self.status = ConnectorStatus.HEALTHY
            return True

        # Real authentication logic here
        self._token = api_key
        self.status = ConnectorStatus.HEALTHY
        return True

    async def execute(self, action: str, parameters: dict[str, Any]) -> ConnectorResult:
        if action not in self.supported_actions:
            return ConnectorResult(success=False, error=f"Unknown action: {action}")

        audit = self._create_audit_entry(action, parameters)

        handler = getattr(self, f"_action_{action}", None)
        if handler is None:
            return ConnectorResult(success=False, error=f"Action not implemented: {action}")

        try:
            data = await handler(parameters)
            audit.result_status = "success"
            return ConnectorResult(success=True, data=data, audit_entry=audit)
        except Exception as e:
            audit.result_status = "error"
            audit.error = str(e)
            return ConnectorResult(success=False, error=str(e), audit_entry=audit)

    async def healthcheck(self) -> ConnectorStatus:
        if self._token:
            self.status = ConnectorStatus.HEALTHY
        else:
            self.status = ConnectorStatus.NOT_CONFIGURED
        return self.status

    # -- Action handlers --

    async def _action_list_items(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"items": [], "total": 0}

    async def _action_create_item(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"id": "new-item-id", "status": "created"}
```

### 3. Register the connector

Add your connector to the registry in `services/connectors/src/framework/registry.py`:

```python
async def load_connectors(self) -> None:
    from ..connectors.entra_id.connector import EntraIDConnector
    from ..connectors.servicenow.connector import ServiceNowConnector
    from ..connectors.my_system.connector import MySystemConnector

    for cls in [EntraIDConnector, ServiceNowConnector, MySystemConnector]:
        instance = cls()
        self.connectors[instance.name] = instance
```

That's it. Your connector is now accessible via:
- `GET /api/v1/connectors` — appears in the connector list
- `POST /api/v1/connectors/my_system/execute` — execute actions

## Key Patterns

### Stub Mode

All connectors should support running without real credentials for local development. Check for required credentials and fall back to stub data:

```python
if not all([api_url, api_key]):
    self._token = "stub"
    self.status = ConnectorStatus.HEALTHY
    return True
```

### Action Handler Convention

Actions are dispatched by naming convention: `_action_{action_name}`. The `execute()` method looks up handlers via `getattr(self, f"_action_{action}")`.

Each handler receives the raw `parameters` dict and returns a result dict. Keep handlers focused — one handler per API operation.

### Audit Trail

Every `execute()` call should create an audit entry before running the action:

```python
audit = self._create_audit_entry(action, parameters)
```

The `AuditEntry` records:
- `connector_name` — auto-populated from `self.name`
- `action` — the action being executed
- `correlation_id` — for tracing across services (auto-generated UUID if not provided)
- `parameters` — the input parameters (be careful with sensitive data)
- `result_status` — set to `"success"` or `"error"` after execution

### Permission Scopes

Declare all permissions the connector requires from the target system:

```python
required_permissions = (
    PermissionScope("items.read", "Read items"),
    PermissionScope("items.write", "Create and update items", required=False),
)
```

Set `required=False` for optional permissions that enable additional features but aren't strictly necessary.

### Health Checks

The `healthcheck()` method should verify connectivity to the target system. Return one of:

| Status           | Meaning |
|-----------------|---------|
| `HEALTHY`       | Connected and operational |
| `DEGRADED`      | Connected but experiencing issues (e.g., rate-limited) |
| `UNAVAILABLE`   | Cannot reach the target system |
| `NOT_CONFIGURED`| No credentials provided |

For a thorough healthcheck, make a lightweight API call (see the Entra ID connector's `GET /organization` check).

## Existing Connectors

### Entra ID (`services/connectors/src/connectors/entra_id/`)

- Integrates with Microsoft Graph API for identity and access management
- OAuth2 client credentials via MSAL
- 10 actions: user CRUD, group management, role assignment, session revocation
- Required permissions: `User.ReadWrite.All`, `Group.ReadWrite.All`, `Directory.ReadWrite.All`, `User.RevokeSessions.All`

### ServiceNow (`services/connectors/src/connectors/servicenow/`)

- Integrates with ServiceNow REST API for ITSM operations
- OAuth2 client credentials
- 10 actions: incident lifecycle, assignment, KB search, SLA tracking, escalation
- Required permissions: `incident_write`, `incident_read`, `knowledge_read`, `sla_read`, `assignment_write`

## Testing

Test your connector by starting the connectors service and calling the execute endpoint:

```bash
# Start services
docker-compose up --build connectors

# List connectors (verify yours appears)
curl http://localhost:8002/api/v1/connectors

# Execute an action (stub mode)
curl -X POST http://localhost:8002/api/v1/connectors/my_system/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "list_items", "parameters": {}}'
```

For integration testing with real APIs, provide credentials via environment variables or a secrets manager and verify the full authenticate → execute → healthcheck lifecycle.
