"""Watch-layer ingest service.

Accepts event batches from the desktop agent (Tauri) and the browser extension (MV3), validates
them against the privacy-by-design event schema, normalises them, and forwards to NATS JetStream.

Business-plan references:
    §4.1.1 — Observation Layer (Watch)
    §5.2   — 9-step platform loop, steps 1–2
    §11A.5 — Employee monitoring law, product response #3 (observation scope)
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .privacy import CONTENT_FIELD_DENYLIST, PrivacyViolation, strip_and_validate

logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
STREAM_NAME = os.getenv("OBSERVATION_STREAM", "OBSERVATION")
SUBJECT_PREFIX = os.getenv("OBSERVATION_SUBJECT_PREFIX", "observation.events")


# ---------------------------------------------------------------------------
# Wire format — canonical Watch-layer event schema.
#
# Any change here is a breaking change for the desktop agent and the browser
# extension. Keep it narrow and boring.
# ---------------------------------------------------------------------------
class ObservationEvent(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    actor_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime
    action_type: str = Field(..., min_length=1, max_length=64)
    source_application: str = Field(default="", max_length=128)
    target_application: str = Field(default="", max_length=128)
    duration_ms: int = Field(default=0, ge=0)
    capture_channel: Literal["desktop", "browser", "api_tap"]
    metadata: dict = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def _metadata_must_not_contain_content(cls, v: dict) -> dict:
        for banned in CONTENT_FIELD_DENYLIST:
            if banned in v:
                raise ValueError(
                    f"metadata contains disallowed content field '{banned}'. "
                    "Observation events carry metadata only (see §11A.5, docs/adr/008)."
                )
        return v


class EventBatch(BaseModel):
    events: list[ObservationEvent]


class IngestSink:
    """Thin NATS-or-stub sink. Fails soft in dev; fails loud when NATS is expected."""

    def __init__(self) -> None:
        self._nc = None
        self._js = None

    async def connect(self) -> None:
        try:
            import nats
        except ImportError:
            logger.warning("nats-py not installed — ingest running in stub mode (log-only)")
            return
        try:
            self._nc = await nats.connect(NATS_URL)
            self._js = self._nc.jetstream()
            try:
                await self._js.add_stream(
                    name=STREAM_NAME, subjects=[f"{SUBJECT_PREFIX}.>"]
                )
            except Exception:
                pass
            logger.info("ingest sink connected: %s (stream=%s)", NATS_URL, STREAM_NAME)
        except Exception:
            logger.warning("NATS connection failed (%s) — stub mode", NATS_URL, exc_info=True)

    async def publish(self, event: ObservationEvent) -> None:
        subject = f"{SUBJECT_PREFIX}.{event.tenant_id}.{event.capture_channel}"
        payload = event.model_dump_json().encode()
        if self._js is not None:
            await self._js.publish(subject, payload)
            return
        # Stub path — never persist, just log.
        logger.info("[stub] would publish %s bytes to %s", len(payload), subject)

    async def disconnect(self) -> None:
        if self._nc is not None:
            await self._nc.drain()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    sink = IngestSink()
    await sink.connect()
    app.state.sink = sink
    yield
    await sink.disconnect()


app = FastAPI(
    title="Ant Automations — Observation Ingest",
    version="0.1.0",
    description=(
        "Watch-layer ingest for desktop-agent and browser-extension events. "
        "Validates privacy schema, normalises, publishes to NATS JetStream."
    ),
    lifespan=lifespan,
)


@app.get("/healthz")
async def health() -> dict:
    sink: IngestSink = app.state.sink
    return {
        "status": "ok" if sink._nc is not None else "degraded",
        "service": "observation-ingest",
        "nats": sink._nc is not None,
    }


@app.post("/api/v1/events/batch")
async def ingest_batch(batch: EventBatch) -> dict:
    """Accept a batch of events from an agent or extension."""
    sink: IngestSink = app.state.sink
    accepted = 0
    for event in batch.events:
        try:
            # Double defence: Pydantic validator ran at parse time, strip_and_validate
            # is the second pass that scans every nested JSON leaf for banned keys.
            strip_and_validate(event.model_dump())
        except PrivacyViolation as exc:
            raise HTTPException(status_code=400, detail=f"privacy violation: {exc}")
        await sink.publish(event)
        accepted += 1
    return {"accepted": accepted, "received_at": datetime.now(UTC).isoformat()}


@app.get("/api/v1/observation/status/{actor_id}")
async def observation_status(actor_id: str) -> dict:
    """Minimum viable employee-transparency endpoint.

    The desktop agent tray and the extension popup call this to show observation status to the
    observed employee. The real implementation will read from a Redis last-event cache; for now
    we respond with a static, non-PII shape so client development isn't blocked.

    TODO(v4.5-watch): back with Redis cache populated by the ingest path.
    """
    return {
        "actor_id": actor_id,
        "observation_active": True,
        "paused": False,
        "scope": "minimal",
        "categories_captured": ["application_switch", "navigation", "form_submission_event"],
        "categories_not_captured": [
            "keystrokes",
            "clipboard_content",
            "form_values",
            "screen_content",
            "file_contents",
        ],
        "last_event_at": None,
    }


@app.get("/api/v1/schema/event")
async def event_schema() -> dict:
    """Expose the canonical wire schema so clients can check compatibility at startup."""
    return json.loads(ObservationEvent.model_json_schema().__str__().replace("'", '"'))
