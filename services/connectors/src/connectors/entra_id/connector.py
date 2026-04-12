"""Microsoft Entra ID connector — identity and access management.

Supports user lifecycle (create, disable, delete), group management,
role assignment, and authentication operations via Microsoft Graph API.
Uses MSAL for OAuth2 client credentials with scoped permissions.

When credentials are provided, all actions call the real Graph API.
Without credentials (local dev), returns stub data.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...framework.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    PermissionScope,
)

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class EntraIDConnector(BaseConnector):
    name = "entra_id"
    supported_actions = (
        "create_user",
        "disable_user",
        "delete_user",
        "get_user",
        "list_users",
        "assign_group",
        "remove_group",
        "list_groups",
        "assign_role",
        "revoke_all_sessions",
    )
    required_permissions = (
        PermissionScope("User.ReadWrite.All", "Create, update, and delete users"),
        PermissionScope("Group.ReadWrite.All", "Manage group memberships"),
        PermissionScope("Directory.ReadWrite.All", "Manage directory roles"),
        PermissionScope("User.RevokeSessions.All", "Revoke user sign-in sessions"),
    )

    def __init__(self) -> None:
        self._token: str | None = None
        self._tenant_id: str | None = None
        self._client_id: str | None = None
        self._http: httpx.AsyncClient | None = None

    async def authenticate(self, credentials: dict[str, str]) -> bool:
        """Authenticate via OAuth2 client credentials flow against Azure AD.

        Expected credentials:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            client_secret: Client secret value
        """
        self._tenant_id = credentials.get("tenant_id")
        self._client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")

        if not all([self._tenant_id, self._client_id, client_secret]):
            logger.warning("Entra ID credentials incomplete — running in stub mode")
            self._token = "stub"
            self.status = ConnectorStatus.HEALTHY
            return True

        token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]

        self._http = httpx.AsyncClient(
            base_url=GRAPH_BASE,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            timeout=30.0,
        )
        self.status = ConnectorStatus.HEALTHY
        logger.info("Entra ID authenticated (tenant=%s)", self._tenant_id)
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
        except httpx.HTTPStatusError as e:
            audit.result_status = "error"
            audit.error = f"Graph API {e.response.status_code}: {e.response.text[:200]}"
            return ConnectorResult(success=False, error=audit.error, audit_entry=audit)
        except Exception as e:
            audit.result_status = "error"
            audit.error = str(e)
            return ConnectorResult(success=False, error=str(e), audit_entry=audit)

    async def healthcheck(self) -> ConnectorStatus:
        if self._http:
            try:
                resp = await self._http.get("/organization")
                resp.raise_for_status()
                self.status = ConnectorStatus.HEALTHY
            except Exception:
                self.status = ConnectorStatus.DEGRADED
        elif self._token:
            self.status = ConnectorStatus.HEALTHY
        else:
            self.status = ConnectorStatus.NOT_CONFIGURED
        return self.status

    # -- Graph API helper ------------------------------------------------------

    async def _graph(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Call the Graph API, falling back to None in stub mode."""
        if not self._http:
            return None
        resp = await self._http.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp

    # -- Action handlers -------------------------------------------------------

    async def _action_create_user(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST https://graph.microsoft.com/v1.0/users
        body = {
            "accountEnabled": True,
            "displayName": params.get("display_name", params.get("email", "")),
            "mailNickname": params.get("email", "").split("@")[0],
            "userPrincipalName": params.get("email", ""),
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": params.get("temp_password", "TempPass!2026"),
            },
            "department": params.get("department", ""),
        }
        resp = await self._graph("POST", "/users", json=body)
        if resp:
            data = resp.json()
            return {"user_id": data["id"], "email": data["userPrincipalName"], "status": "created"}
        return {"user_id": f"stub-{params.get('email')}", "email": params.get("email"), "status": "created"}

    async def _action_disable_user(self, params: dict[str, Any]) -> dict[str, Any]:
        # PATCH https://graph.microsoft.com/v1.0/users/{id}
        user_id = params["user_id"]
        resp = await self._graph("PATCH", f"/users/{user_id}", json={"accountEnabled": False})
        if resp:
            return {"user_id": user_id, "status": "disabled"}
        return {"user_id": user_id, "status": "disabled"}

    async def _action_delete_user(self, params: dict[str, Any]) -> dict[str, Any]:
        # DELETE https://graph.microsoft.com/v1.0/users/{id}
        user_id = params["user_id"]
        await self._graph("DELETE", f"/users/{user_id}")
        return {"user_id": user_id, "status": "deleted"}

    async def _action_get_user(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET https://graph.microsoft.com/v1.0/users/{id}
        user_id = params["user_id"]
        resp = await self._graph("GET", f"/users/{user_id}")
        if resp:
            data = resp.json()
            return {"user_id": data["id"], "email": data.get("userPrincipalName"), "exists": True}
        return {"user_id": user_id, "exists": True}

    async def _action_list_users(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET https://graph.microsoft.com/v1.0/users
        resp = await self._graph("GET", "/users", params={"$top": params.get("limit", 100)})
        if resp:
            data = resp.json()
            return {"users": data.get("value", []), "total": len(data.get("value", []))}
        return {"users": [], "total": 0}

    async def _action_assign_group(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST https://graph.microsoft.com/v1.0/groups/{group-id}/members/$ref
        group_id = params["group"]
        user_id = params["user_id"]
        body = {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{user_id}"}
        await self._graph("POST", f"/groups/{group_id}/members/$ref", json=body)
        return {"user_id": user_id, "group": group_id, "status": "assigned"}

    async def _action_remove_group(self, params: dict[str, Any]) -> dict[str, Any]:
        # DELETE https://graph.microsoft.com/v1.0/groups/{group-id}/members/{user-id}/$ref
        group_id = params["group"]
        user_id = params["user_id"]
        await self._graph("DELETE", f"/groups/{group_id}/members/{user_id}/$ref")
        return {"user_id": user_id, "group": group_id, "status": "removed"}

    async def _action_list_groups(self, params: dict[str, Any]) -> dict[str, Any]:
        # GET https://graph.microsoft.com/v1.0/groups
        resp = await self._graph("GET", "/groups", params={"$top": params.get("limit", 100)})
        if resp:
            data = resp.json()
            return {"groups": data.get("value", []), "total": len(data.get("value", []))}
        return {"groups": [], "total": 0}

    async def _action_assign_role(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments
        body = {
            "principalId": params["user_id"],
            "roleDefinitionId": params["role"],
            "directoryScopeId": "/",
        }
        resp = await self._graph("POST", "/roleManagement/directory/roleAssignments", json=body)
        if resp:
            return {"user_id": params["user_id"], "role": params["role"], "status": "assigned"}
        return {"user_id": params["user_id"], "role": params["role"], "status": "assigned"}

    async def _action_revoke_all_sessions(self, params: dict[str, Any]) -> dict[str, Any]:
        # POST https://graph.microsoft.com/v1.0/users/{id}/revokeSignInSessions
        user_id = params["user_id"]
        resp = await self._graph("POST", f"/users/{user_id}/revokeSignInSessions")
        if resp:
            return {"user_id": user_id, "sessions_revoked": resp.json().get("value", True)}
        return {"user_id": user_id, "sessions_revoked": True}
