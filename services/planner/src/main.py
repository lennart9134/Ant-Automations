"""Planner service — LangGraph orchestration for Ant Automations workflows.

Connects to NATS for publishing task execution requests to the workers
service. Workflow results are returned synchronously but actions that
need connector execution are dispatched asynchronously via NATS.
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .graph.engine import WorkflowEngine

logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")


class EventBus:
    """Thin NATS publisher for dispatching tasks to workers."""

    def __init__(self) -> None:
        self._nc = None

    async def connect(self) -> None:
        try:
            import nats

            self._nc = await nats.connect(NATS_URL)
            logger.info("Planner NATS connected (%s)", NATS_URL)
        except ImportError:
            logger.warning("nats-py not installed — event bus disabled")
        except Exception:
            logger.warning("NATS connection failed — event bus disabled", exc_info=True)

    async def publish(self, subject: str, payload: dict) -> None:
        if self._nc:
            await self._nc.publish(subject, json.dumps(payload).encode())

    async def disconnect(self) -> None:
        if self._nc:
            await self._nc.drain()

    @property
    def connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected if self._nc else False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Event bus
    bus = EventBus()
    await bus.connect()
    app.state.event_bus = bus

    # Workflow engine
    engine = WorkflowEngine()
    engine.event_bus = bus
    await engine.start()
    app.state.engine = engine

    yield

    await engine.stop()
    await bus.disconnect()


app = FastAPI(title="Ant Automations Planner", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    bus: EventBus = app.state.event_bus
    return {"status": "ok", "service": "planner", "nats": bus.connected}


@app.post("/api/v1/workflows/{workflow_name}/run")
async def run_workflow(workflow_name: str, payload: dict) -> dict:
    """Trigger a workflow execution through the LangGraph engine."""
    engine: WorkflowEngine = app.state.engine
    result = await engine.execute(workflow_name, payload)

    # Only dispatch to NATS if NOT in shadow mode
    bus: EventBus = app.state.event_bus
    if not result.shadow and bus.connected and result.results:
        for action in result.results:
            if isinstance(action, dict) and action.get("action_type"):
                await bus.publish(
                    "tasks.connector_action",
                    {
                        "type": "connector_action",
                        "task_id": result.run_id,
                        "connector": "entra_id",
                        "action": action["action_type"],
                        "parameters": action.get("parameters", {}),
                    },
                )

    return {
        "workflow": workflow_name,
        "run_id": result.run_id,
        "status": result.status,
        "shadow": result.shadow,
    }


@app.get("/api/v1/shadow-log")
async def get_shadow_log() -> dict:
    """Return the shadow mode execution log — shows what the system would do without actually doing it."""
    engine: WorkflowEngine = app.state.engine
    entries = engine.get_shadow_log()
    return {"entries": entries, "total": len(entries)}
