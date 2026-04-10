"""Connector registry — discovers and manages connector instances."""

from __future__ import annotations

from .base import BaseConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self.connectors: dict[str, BaseConnector] = {}

    async def load_connectors(self) -> None:
        from ..connectors.entra_id.connector import EntraIDConnector
        from ..connectors.servicenow.connector import ServiceNowConnector

        for cls in [EntraIDConnector, ServiceNowConnector]:
            instance = cls()
            self.connectors[instance.name] = instance

    def get(self, name: str) -> BaseConnector:
        if name not in self.connectors:
            raise KeyError(f"Connector not found: {name}")
        return self.connectors[name]
