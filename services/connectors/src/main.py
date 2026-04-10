"""Connectors service — manages business-system connector lifecycle and execution."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .framework.registry import ConnectorRegistry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    registry = ConnectorRegistry()
    await registry.load_connectors()
    app.state.registry = registry
    yield


app = FastAPI(title="Ant Automations Connectors", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "connectors"}


@app.get("/api/v1/connectors")
async def list_connectors() -> list[dict]:
    registry: ConnectorRegistry = app.state.registry
    return [
        {"name": name, "status": conn.status, "actions": list(conn.supported_actions)}
        for name, conn in registry.connectors.items()
    ]


@app.post("/api/v1/connectors/{connector_name}/execute")
async def execute_action(connector_name: str, payload: dict) -> dict:
    registry: ConnectorRegistry = app.state.registry
    connector = registry.get(connector_name)
    result = await connector.execute(payload["action"], payload.get("parameters", {}))
    return result.to_dict()
