"""Multi-tenant configuration service.

Manages per-tenant settings including workflow templates, connector configs,
approval policies, and feature flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    domain: str = ""
    workflow_templates: dict[str, dict[str, Any]] = field(default_factory=dict)
    connector_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    approval_policies: dict[str, Any] = field(default_factory=dict)
    feature_flags: dict[str, bool] = field(default_factory=dict)
    data_residency: str = "eu-west-1"
    retention_days: int = 90


class TenantService:
    """Manages tenant lifecycle and configuration."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantConfig] = {}

    def create(self, tenant_id: str, name: str, **kwargs: Any) -> TenantConfig:
        config = TenantConfig(tenant_id=tenant_id, name=name, **kwargs)
        self._tenants[tenant_id] = config
        return config

    def get(self, tenant_id: str) -> TenantConfig | None:
        return self._tenants.get(tenant_id)

    def update(self, tenant_id: str, **updates: Any) -> TenantConfig:
        config = self._tenants[tenant_id]
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    def list_tenants(self) -> list[TenantConfig]:
        return list(self._tenants.values())

    def set_workflow_template(
        self,
        tenant_id: str,
        department: str,
        template: dict[str, Any],
    ) -> None:
        config = self._tenants[tenant_id]
        config.workflow_templates[department] = template

    def set_connector_config(
        self,
        tenant_id: str,
        connector_name: str,
        connector_config: dict[str, Any],
    ) -> None:
        config = self._tenants[tenant_id]
        config.connector_configs[connector_name] = connector_config
