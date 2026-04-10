"""Base connector — abstract interface for all business-system connectors."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ConnectorStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass
class PermissionScope:
    """Declares a permission the connector requires from the target system."""

    name: str
    description: str
    required: bool = True


@dataclass
class ConnectorAction:
    """Describes an available action on the connector."""

    name: str
    description: str
    risk_level: str = "medium"  # low, medium, high
    required_permissions: list[str] = field(default_factory=list)


@dataclass
class AuditEntry:
    """Immutable audit record produced by every connector execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    connector_name: str = ""
    action: str = ""
    correlation_id: str = ""
    actor: str = ""
    target: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    result_status: str = ""
    error: str | None = None


@dataclass
class ConnectorResult:
    """Result of a connector action execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    audit_entry: AuditEntry | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseConnector(ABC):
    """Abstract base for all Ant Automations connectors.

    Subclasses must implement authenticate(), execute(), and healthcheck().
    The framework handles audit trail generation, permission validation,
    and scoped service identity enforcement.
    """

    name: str = ""
    status: ConnectorStatus = ConnectorStatus.NOT_CONFIGURED
    supported_actions: tuple[str, ...] = ()
    required_permissions: tuple[PermissionScope, ...] = ()

    @abstractmethod
    async def authenticate(self, credentials: dict[str, str]) -> bool:
        """Authenticate with the target system using scoped service identity."""
        ...

    @abstractmethod
    async def execute(self, action: str, parameters: dict[str, Any]) -> ConnectorResult:
        """Execute an action against the target system."""
        ...

    @abstractmethod
    async def healthcheck(self) -> ConnectorStatus:
        """Check connectivity and health of the target system."""
        ...

    def _create_audit_entry(
        self,
        action: str,
        parameters: dict[str, Any],
        correlation_id: str = "",
    ) -> AuditEntry:
        return AuditEntry(
            connector_name=self.name,
            action=action,
            correlation_id=correlation_id or str(uuid.uuid4()),
            parameters=parameters,
        )
