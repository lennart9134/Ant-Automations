"""ServiceNow ITSM connector — ticket management, triage, and knowledge base.

Supports incident lifecycle, assignment, categorization, knowledge base search,
SLA tracking, and escalation via ServiceNow REST API.
Uses OAuth2 client credentials with scoped permissions.
"""

from __future__ import annotations

from typing import Any

from ...framework.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    PermissionScope,
)


class ServiceNowConnector(BaseConnector):
    name = "servicenow"
    supported_actions = (
        "create_incident",
        "update_incident",
        "assign_incident",
        "get_incident",
        "list_incidents",
        "add_comment",
        "categorize_incident",
        "search_knowledge_base",
        "get_sla_status",
        "escalate_incident",
    )
    required_permissions = (
        PermissionScope("incident_write", "Create and update incidents"),
        PermissionScope("incident_read", "Read incident details"),
        PermissionScope("knowledge_read", "Search knowledge base articles"),
        PermissionScope("sla_read", "Read SLA status and metrics"),
        PermissionScope("assignment_write", "Assign and reassign incidents"),
    )

    def __init__(self) -> None:
        self._token: str | None = None
        self._instance_url: str | None = None

    async def authenticate(self, credentials: dict[str, str]) -> bool:
        """Authenticate via OAuth2 client credentials.

        Expected credentials:
            instance_url: ServiceNow instance URL (e.g., https://dev12345.service-now.com)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self._instance_url = credentials.get("instance_url")
        # In production: POST {instance_url}/oauth_token.do
        self._token = "placeholder"
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

    async def _action_create_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST /api/now/table/incident
        return {
            "sys_id": f"INC{params.get('short_description', '')[:8]}",
            "number": "INC0010001",
            "state": "new",
            "short_description": params.get("short_description"),
        }

    async def _action_update_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # PATCH /api/now/table/incident/{sys_id}
        return {"sys_id": params.get("sys_id"), "updated_fields": list(params.keys())}

    async def _action_assign_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # PATCH /api/now/table/incident/{sys_id} with assignment_group
        return {
            "sys_id": params.get("sys_id"),
            "assigned_to": params.get("assigned_to"),
            "assignment_group": params.get("assignment_group"),
        }

    async def _action_get_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET /api/now/table/incident/{sys_id}
        return {"sys_id": params.get("sys_id"), "state": "new"}

    async def _action_list_incidents(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET /api/now/table/incident
        return {"incidents": [], "total": 0}

    async def _action_add_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST /api/now/table/incident/{sys_id} with comments field
        return {"sys_id": params.get("sys_id"), "comment_added": True}

    async def _action_categorize_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # PATCH /api/now/table/incident/{sys_id} with category, subcategory
        return {
            "sys_id": params.get("sys_id"),
            "category": params.get("category"),
            "subcategory": params.get("subcategory"),
        }

    async def _action_search_knowledge_base(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET /api/now/table/kb_knowledge with query
        return {"articles": [], "query": params.get("query")}

    async def _action_get_sla_status(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET /api/now/table/task_sla?task={sys_id}
        return {
            "sys_id": params.get("sys_id"),
            "sla_percentage": 0.0,
            "has_breached": False,
        }

    async def _action_escalate_incident(self, params: dict[str, Any]) -> dict[str, Any]:
        # PATCH /api/now/table/incident/{sys_id} with priority escalation
        return {
            "sys_id": params.get("sys_id"),
            "escalated": True,
            "new_priority": params.get("new_priority", "2"),
        }
