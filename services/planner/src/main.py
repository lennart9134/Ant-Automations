"""Planner service — LangGraph orchestration for Ant Automations workflows."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .graph.engine import WorkflowEngine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.engine = WorkflowEngine()
    await app.state.engine.start()
    yield
    await app.state.engine.stop()


app = FastAPI(title="Ant Automations Planner", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "planner"}


@app.post("/api/v1/workflows/{workflow_name}/run")
async def run_workflow(workflow_name: str, payload: dict) -> dict:
    """Trigger a workflow execution through the LangGraph engine."""
    engine: WorkflowEngine = app.state.engine
    result = await engine.execute(workflow_name, payload)
    return {"workflow": workflow_name, "run_id": result.run_id, "status": result.status}
