"""Tests for the Entra ID connector."""

import pytest

from src.connectors.entra_id.connector import EntraIDConnector
from src.framework.base import ConnectorStatus


@pytest.fixture
def connector():
    return EntraIDConnector()


@pytest.mark.asyncio
async def test_authenticate(connector):
    result = await connector.authenticate({
        "tenant_id": "test-tenant",
        "client_id": "test-client",
        "client_secret": "test-secret",
    })
    assert result is True
    assert connector.status == ConnectorStatus.HEALTHY


@pytest.mark.asyncio
async def test_create_user(connector):
    await connector.authenticate({"tenant_id": "t", "client_id": "c", "client_secret": "s"})
    result = await connector.execute("create_user", {"email": "test@example.com", "department": "engineering"})
    assert result.success is True
    assert result.data["status"] == "created"


@pytest.mark.asyncio
async def test_unknown_action(connector):
    result = await connector.execute("nonexistent_action", {})
    assert result.success is False
    assert "Unknown action" in result.error


@pytest.mark.asyncio
async def test_supported_actions():
    connector = EntraIDConnector()
    assert "create_user" in connector.supported_actions
    assert "revoke_all_sessions" in connector.supported_actions
    assert len(connector.supported_actions) == 10
