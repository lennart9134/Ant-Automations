"""Workers service — task execution pool for connector actions and tool calls."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # In production: connect to NATS, start worker pool
    yield


app = FastAPI(title="Ant Automations Workers", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "workers"}


@app.get("/api/v1/workers/status")
async def worker_status() -> dict:
    return {
        "pool_size": 0,
        "active": 0,
        "queued": 0,
    }
