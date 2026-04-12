"""Workers service — NATS-backed task execution pool for connector actions and tool calls.

Subscribes to ``tasks.>`` subjects on NATS JetStream. Each message is
deserialized into a task dict and dispatched to a handler. Results are
published back to ``results.{task_id}``.

Configuration:
    NATS_URL: NATS server URL (default nats://localhost:4222)
    WORKER_CONCURRENCY: max concurrent handlers (default 10)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "10"))


class WorkerPool:
    """Manages NATS subscriptions and concurrent task execution."""

    def __init__(self) -> None:
        self._nc = None  # nats.aio.client.Client
        self._js = None  # JetStream context
        self._sub = None
        self._tasks: dict[str, dict] = {}
        self._active: int = 0
        self._completed: int = 0
        self._semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)

    async def connect(self) -> None:
        try:
            import nats

            self._nc = await nats.connect(NATS_URL)
            self._js = self._nc.jetstream()
            # Create stream if it doesn't exist
            try:
                await self._js.add_stream(name="TASKS", subjects=["tasks.>"])
            except Exception:
                pass  # Stream may already exist
            # Subscribe to all task subjects
            self._sub = await self._js.subscribe("tasks.>", durable="workers")
            logger.info("NATS connected (%s), worker pool ready", NATS_URL)
        except ImportError:
            logger.warning("nats-py not installed — worker pool running in stub mode")
        except Exception:
            logger.warning("NATS connection failed (%s) — running in stub mode", NATS_URL, exc_info=True)

    async def start_consuming(self) -> None:
        """Start the message consumption loop."""
        if not self._sub:
            return
        asyncio.create_task(self._consume_loop())

    async def _consume_loop(self) -> None:
        """Pull messages and dispatch to handlers with concurrency control."""
        while self._sub:
            try:
                msgs = await self._sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    asyncio.create_task(self._handle_message(msg))
            except Exception:
                await asyncio.sleep(1)

    async def _handle_message(self, msg) -> None:
        async with self._semaphore:
            self._active += 1
            task_id = str(uuid.uuid4())
            try:
                payload = json.loads(msg.data.decode())
                self._tasks[task_id] = {
                    "id": task_id,
                    "payload": payload,
                    "status": "running",
                    "started_at": datetime.now(UTC).isoformat(),
                }

                # Dispatch based on task type
                result = await self._execute_task(payload)

                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["result"] = result
                self._completed += 1

                # Publish result back to NATS
                if self._nc:
                    result_subject = f"results.{payload.get('task_id', task_id)}"
                    await self._nc.publish(result_subject, json.dumps(result).encode())

                await msg.ack()
            except Exception:
                self._tasks[task_id]["status"] = "failed"
                logger.exception("Task %s failed", task_id)
                await msg.nak()
            finally:
                self._active -= 1

    async def _execute_task(self, payload: dict) -> dict:
        """Execute a task based on its type. Extensible dispatch."""
        task_type = payload.get("type", "unknown")
        if task_type == "connector_action":
            return await self._handle_connector_action(payload)
        if task_type == "workflow_step":
            return await self._handle_workflow_step(payload)
        return {"status": "completed", "task_type": task_type, "result": "noop"}

    async def _handle_connector_action(self, payload: dict) -> dict:
        """Execute a connector action (delegated to connector service)."""
        return {
            "status": "completed",
            "connector": payload.get("connector"),
            "action": payload.get("action"),
            "result": payload.get("parameters", {}),
        }

    async def _handle_workflow_step(self, payload: dict) -> dict:
        """Execute a workflow step."""
        return {
            "status": "completed",
            "workflow": payload.get("workflow"),
            "step": payload.get("step"),
        }

    async def disconnect(self) -> None:
        if self._sub:
            await self._sub.unsubscribe()
        if self._nc:
            await self._nc.drain()
            logger.info("NATS disconnected")

    @property
    def stats(self) -> dict:
        return {
            "pool_size": WORKER_CONCURRENCY,
            "active": self._active,
            "completed": self._completed,
            "queued": len([t for t in self._tasks.values() if t["status"] == "running"]),
            "connected": self._nc is not None and self._nc.is_connected if self._nc else False,
        }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = WorkerPool()
    await pool.connect()
    await pool.start_consuming()
    app.state.pool = pool
    yield
    await pool.disconnect()


app = FastAPI(title="Ant Automations Workers", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    pool: WorkerPool = app.state.pool
    connected = pool._nc is not None
    return {"status": "ok" if connected else "degraded", "service": "workers", "nats": connected}


@app.get("/api/v1/workers/status")
async def worker_status() -> dict:
    return app.state.pool.stats


@app.post("/api/v1/workers/submit")
async def submit_task(payload: dict) -> dict:
    """Submit a task directly via HTTP (bypassing NATS for testing)."""
    pool: WorkerPool = app.state.pool
    if pool._nc:
        subject = f"tasks.{payload.get('type', 'generic')}"
        await pool._nc.publish(subject, json.dumps(payload).encode())
        return {"status": "queued", "subject": subject}
    # Stub mode — execute inline
    result = await pool._execute_task(payload)
    return {"status": "executed_inline", "result": result}
